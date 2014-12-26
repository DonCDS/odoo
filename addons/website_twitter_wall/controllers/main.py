import base64
import mimetypes
from urllib2 import Request, urlopen
from oauth import oauth
from openerp.addons.web import http
from openerp.addons.web.http import request
from token import *

class website_twitter_wall(http.Controller):

    _tweet_per_page = 10

    @http.route('/create_twitter_wall', type='http', auth='user', website=True)
    def create_twitter_wall(self, image=None, wall_name=None, screen_name=None, wall_description=None, publish=False, **kw):
        values = {
            'name': wall_name,
            'description': wall_description,
            'website_id': 1,
            'state': 'not_streaming',
            'website_published': True if publish == 'true' else False,
            'user_id': request.uid
        }
        if 'http' in image or 'https' in image:
            mmtp = mimetypes.guess_type(image, strict = True)
            if not mmtp[0]:
                return False
            ext = mimetypes.guess_extension(mmtp[0])
            f = open("tmp" + ext, 'wb')
            req = Request(image, headers = {'User-Agent': 'Mozilla/5.0'})
            f.write(urlopen(req).read())
            f.close()
            values['image'] = open("tmp" + ext, "rb").read().encode("base64").replace("\n", "")
        else:
            values['image'] = image
        request.env['website.twitter.wall'].create(values)
        return http.local_redirect("/twitter_walls")

    @http.route('/twitter_walls', type='http', auth='public', website=True)
    def twitter_walls(self):
        domain = []
        if request.env.user.id == request.website.user_id.id:
            domain = [('website_published', '=', True), ('state', 'in', ['streaming', 'story'])]
        values = {
            'walls': request.env['website.twitter.wall'].search(domain),
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        return request.website.render("website_twitter_wall.twitter_walls", values)

    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>'], type='http', auth="public", website=True)
    def twitter_wall(self, wall):
        wall.start_incoming_tweets()
        return request.website.render("website_twitter_wall.twitter_wall", {'wall_id': wall.id, 'uid': request.session.uid or False})

    @http.route(['/twitter_wall/push_tweet/<model("website.twitter.wall"):wall>'], method=['POST'], type='json', auth='public', website=True)
    def push_tweet(self, wall, **args):
        wall.create_tweets(args)
        return True

    @http.route('/twitter_wall/pull_tweet/<model("website.twitter.wall"):wall>', type='json', auth="public", website=True)
    def pull_tweet(self, wall, last_tweet=None):
        tweet = False
        domain = [('wall_id', '=', wall.id)]
        if last_tweet:
            domain += [('id', '>', last_tweet)]
        tweets = request.env['website.twitter.wall.tweet'].search_read(domain, [], offset = 0, limit = 1, order = 'id desc')
        if tweets and tweets[-1].get('id') != last_tweet:
            tweet = tweets[-1]
        return tweet

    @http.route(['/twitter_wall/story/<model("website.twitter.wall"):wall>',
                '/twitter_wall/story/<model("website.twitter.wall"):wall>/page/<int:page>'], type='http', auth="public", website=True)
    def twitter_wall_archieve(self, wall, page=1):
        tweet_obj = request.env['website.twitter.wall.tweet']
        if wall.state != 'story':
            wall.write({'state': 'story'})
        domain = [('wall_id', '=', wall.id)]
        pager = request.website.pager(url = "/twitter_wall/story/%s" % (wall.id), total = tweet_obj.search_count(domain), page = page,
                                      step = self._tweet_per_page, scope = self._tweet_per_page, url_args = {})
        tweets = tweet_obj.search(domain, limit = self._tweet_per_page, offset = pager['offset'], order = 'id desc').sudo()
        values = {
            'wall': wall,
            'tweets': tweets,
            'pager': pager,
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        if page == 1:
            wall.write({'number_view': wall.number_view + 1})
        return request.website.render("website_twitter_wall.twitter_wall_archieve", values)

    @http.route(['/twitter_wall/authenticate/<model("website.twitter.wall"):wall>'], type='http', auth="public", website=True)
    def authenticate_twitter_wall(self, wall, **kw):
        twitter_api_key, twitter_api_secret = wall.get_api_keys()
        auth = oauth(twitter_api_key, twitter_api_secret)
        callback_url = "%s/%s/%s" % (request.env['ir.config_parameter'].get_param('web.base.url'), "twitter_callback", wall.id)
        HEADER = auth._generate_header(auth.REQUEST_URL, 'HMAC-SHA1', '1.0', callback_url = callback_url)
        HTTP_REQUEST = Request(auth.REQUEST_URL)
        HTTP_REQUEST.add_header('Authorization', HEADER)
        request_response = urlopen(HTTP_REQUEST, '').read()
        request_response = auth._string_to_dict(request_response)
        if request_response['oauth_token'] and request_response['oauth_callback_confirmed']:
            url = auth.AUTHORIZE_URL + "?oauth_token=" + request_response['oauth_token']
        return request.redirect(url)

    @http.route('/twitter_callback/<model("website.twitter.wall"):wall>', type='http', auth="user")
    def twitter_callback(self, wall, oauth_token, oauth_verifier, **kw):
        twitter_api_key, twitter_api_secret = wall.get_api_keys()
        auth = oauth(twitter_api_key, twitter_api_secret)
        access_token_response = oauth._access_token(auth, oauth_token, oauth_verifier)
        values = {
           'twitter_access_token': access_token_response['oauth_token'],
           'twitter_access_token_secret': access_token_response['oauth_token_secret']
        }
        wall.write(values)
        return http.local_redirect('/twitter_walls')

    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>/delete'], type='http', auth="public", website=True)
    def delete_twitter_wall(self, wall, **kw):
        wall.unlink()
        return http.local_redirect("/twitter_walls", query = request.params)