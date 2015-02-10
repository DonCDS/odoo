from openerp.addons.web import http
from openerp.addons.web.http import request
from oauth import oauth
from base64 import encodestring
from urllib2 import Request, urlopen


class website_twitter_wall(http.Controller):
    # Pagination after 10 tweet in storify view
    _tweet_per_page = 10

    # Create new wall
    @http.route('/create_twitter_wall', type='http', auth='user', website=True)
    def create_twitter_wall(self, name=None, image=None, description=None, publish=False):
        values = {
            'name': name,
            'description': description,
            'website_published': True if publish == 'true' else False,
            'website_id': request.website.id,
            'user_id': request.uid
        }
        if 'http' in image or 'https' in image:
            values['image'] = encodestring(urlopen(image).read())
        else:
            values['image'] = image
        request.env['stream.agent'].create(values)
        return http.local_redirect("/twitter_walls")

    # Display all walls
    @http.route('/twitter_walls', type='http', auth='public', website=True)
    def twitter_walls(self, **args):
        domain = []
        if request.env.user.id == request.website.user_id.id:
            domain = [('website_published', '=', True)]
        values = {
            'walls': request.env['stream.agent'].search(domain),
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        return request.website.render("website_twitter_wall.twitter_walls", values)

    @http.route(['/twitter_wall/<model("stream.agent"):wall>'], type='http', auth="public", website=True)
    def twitter_wall(self, wall):
        if not wall.twitter_access_token:
            return False
        return request.website.render("website_twitter_wall.twitter_wall", {'wall_id': wall.id})

    @http.route('/twitter_wall/pull_tweet/<model("stream.agent"):wall>', type='json', auth="public", website=True)
    def pull_tweet(self, wall, last_tweet=None):
        tweet = False
        domain = [('agent_id', '=', wall.id)]
        if last_tweet:
            domain += [('id', '>', last_tweet)]
        tweets = request.env['twitter.tweet'].search_read(domain, [], offset=0, limit=1, order='id desc')
        if tweets and tweets[-1].get('id') != last_tweet:
            tweet = tweets[-1]
        return tweet

    @http.route(['/twitter_wall/story/<model("stream.agent"):wall>',
                '/twitter_wall/story/<model("stream.agent"):wall>/page/<int:page>'], type='http', auth="public", website=True)
    def twitter_wall_story(self, wall, page=1, **args):
        if not wall.twitter_access_token:
            return False
        tweet_obj = request.env['twitter.tweet']
        domain = [('agent_id', '=', wall.id)]
        pager = request.website.pager(url="/twitter_wall/story/%s" % (wall.id), total=tweet_obj.search_count(domain), page=page,
                                      step=self._tweet_per_page, scope=self._tweet_per_page, url_args={})
        tweets = tweet_obj.search(domain, limit=self._tweet_per_page, offset=pager['offset'], order='id desc').sudo()
        values = {
            'wall': wall,
            'tweets': tweets,
            'pager': pager,
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        if page == 1:
            wall.write({'number_view': wall.number_view + 1})
        return request.website.render("website_twitter_wall.twitter_wall_story", values)

    @http.route(['/twitter_wall/authenticate/<model("stream.agent"):wall>'], type='http', auth="public", website=True)
    def authenticate_twitter_wall(self, wall):
        auth = oauth(wall.stream_id.twitter_api_key, wall.stream_id.twitter_api_secret)
        callback_url = "%s/%s/%s" % (request.env['ir.config_parameter'].get_param('web.base.url'), "twitter_callback", wall.id)
        HEADER = auth._generate_header(auth.REQUEST_URL, 'HMAC-SHA1', '1.0', callback_url=callback_url)
        HTTP_REQUEST = Request(auth.REQUEST_URL)
        HTTP_REQUEST.add_header('Authorization', HEADER)
        request_response = urlopen(HTTP_REQUEST, '').read()
        request_response = auth._string_to_dict(request_response)
        if request_response['oauth_token'] and request_response['oauth_callback_confirmed']:
            url = auth.AUTHORIZE_URL + "?oauth_token=" + request_response['oauth_token']
        return request.redirect(url)

    @http.route('/twitter_callback/<model("stream.agent"):wall>', type='http', auth="user")
    def twitter_callback(self, wall, oauth_token, oauth_verifier):
        auth = oauth(wall.stream_id.twitter_api_key, wall.stream_id.twitter_api_secret)
        access_token_response = oauth._access_token(auth, oauth_token, oauth_verifier)
        wall.write({
            'twitter_access_token': access_token_response['oauth_token'],
            'twitter_access_token_secret': access_token_response['oauth_token_secret'],
            'auth_user': access_token_response['user_id']
        })
        wall.stream_id.restart()
        return http.local_redirect('/twitter_walls')

    # Delete wall
    @http.route(['/twitter_wall/<model("stream.agent"):wall>/delete'], type='http', auth="public", website=True)
    def delete_twitter_wall(self, wall):
        wall.unlink()
        return http.local_redirect("/twitter_walls")
