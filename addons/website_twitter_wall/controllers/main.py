import ast, base64
from urllib2 import urlopen
from datetime import datetime
from urllib2 import Request as URLRequest

from oauth import oauth
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website as controllers
from openerp import SUPERUSER_ID
from openerp.addons.web.controllers.main import login_redirect, ensure_db


class website_twitter_wall(http.Controller):

    _tweet_per_page = 10

    @http.route('/create_twitter_wall', type='http', auth='user', website=True)
    def create_twitter_wall(self, image=None, wall_name= None, screen_name=None, include_retweet=False, wall_description=None, **kw):
        values = {
            'name': wall_name,
            'description': wall_description,
            're_tweet': include_retweet,
            'image': image
        }
        wall_id = request.registry.get('website.twitter.wall').create(request.cr, SUPERUSER_ID, values, request.context)
        return http.local_redirect("/twitter_walls")
    

    @http.route('/twitter_walls', type='http', auth='public', website=True)
    def twitter_walls(self):
        wall_obj = request.registry.get('website.twitter.wall')

        domain = []

        if request.env.user.id == request.website.user_id.id:
            domain += [('website_published', '=', True), ('state', 'in', ['streaming', 'story'])]
    
        wall_ids = wall_obj.search(request.cr, SUPERUSER_ID, domain, context=request.context)
        walls = wall_obj.browse(request.cr, SUPERUSER_ID, wall_ids, context=request.context)
        
        values = {
            'walls': walls,
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        return request.website.render("website_twitter_wall.twitter_walls", values)
    

    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>'], type='http', auth="public", website=True)
    def twitter_wall(self, wall):
        wall_obj = request.registry.get('website.twitter.wall')
        wall_obj.start_incoming_tweets(request.cr, SUPERUSER_ID, [wall.id], context=request.context)
        values = {
            'wall_id' : wall.id,
            'uid': request.session.uid or False
        }
        return request.website.render("website_twitter_wall.twitter_wall", values)


    @http.route(['/twitter_wall/push_tweet/<model("website.twitter.wall"):wall>'], method=['POST'], type='json', auth='public', website=True)
    def push_tweet(self, wall, **args):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        request.registry['website.twitter.wall'].create_tweets(cr, uid, wall.id, args, context)
        return True


    @http.route(['/twitter_wall/story/<model("website.twitter.wall"):wall>',
                '/twitter_wall/story/<model("website.twitter.wall"):wall>/page/<int:page>'], type='http', auth="public", website=True)
    def twitter_wall_archieve(self, wall, page=1):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        wall_obj = request.registry['website.twitter.wall']
        tweet_obj = request.registry['website.twitter.wall.tweet']
        
        if wall.state != 'story':
            wall_obj.write(cr, uid, [wall.id], {'state':'story'})

        domain = [('wall_id','=',wall.id)]

        url = "/twitter_wall/story/%s" % (wall.id)
        pager_count = tweet_obj.search_count(cr, uid, domain)
        pager = request.website.pager(url=url, total=pager_count, page=page,
                                      step=self._tweet_per_page, scope=self._tweet_per_page,
                                      url_args={})
        tweet_ids = tweet_obj.search(cr, uid, domain, limit=self._tweet_per_page, offset=pager['offset'], order='id desc')
        tweets = tweet_obj.browse(cr, uid, tweet_ids)

        values = {
            'wall' : wall,
            'tweets': tweets,
            'pager':pager,
            'is_public_user': request.env.user.id == request.website.user_id.id
        }

        return request.website.render("website_twitter_wall.twitter_wall_archieve", values)


    @http.route(['/twitter_wall/authenticate/<model("website.twitter.wall"):wall>'], type='http', auth="public", website=True)
    def authenticate_twitter_wall(self, wall, **kw):
        twitter_api_key, twitter_api_secret = wall.get_api_keys()

        auth = oauth(twitter_api_key, twitter_api_secret)
        base_url = request.registry.get('ir.config_parameter').get_param(request.cr, SUPERUSER_ID, 'web.base.url')

        callback_url = "%s/%s/%s" % (base_url, "twitter_callback", wall.id)
        HEADER = auth._generate_header(auth.REQUEST_URL, 'HMAC-SHA1', '1.0', callback_url = callback_url)
        
        HTTP_REQUEST = URLRequest(auth.REQUEST_URL)
        HTTP_REQUEST.add_header('Authorization', HEADER)
        request_response = urlopen(HTTP_REQUEST, '').read()
        request_response = auth._string_to_dict(request_response)

        if request_response['oauth_token'] and request_response['oauth_callback_confirmed']:
            url = auth.AUTHORIZE_URL + "?oauth_token=" + request_response['oauth_token']

        return request.redirect(url)
    

    @http.route('/twitter_callback/<model("website.twitter.wall"):wall>', type='http', auth="user")
    def twitter_callback(self, wall, oauth_token, oauth_verifier, **kw):
        twitter_api_key, twitter_api_secret = wall.get_api_keys()
        cr, uid, context = request.cr, SUPERUSER_ID, request.context

        wall_obj = request.registry.get('website.twitter.wall')
        auth = oauth(twitter_api_key, twitter_api_secret)
        access_token_response = oauth._access_token(auth, oauth_token, oauth_verifier)
        values = {
           'twitter_access_token': access_token_response['oauth_token'],
           'twitter_access_token_secret': access_token_response['oauth_token_secret']
        }
        wall_obj.write(cr, uid, [wall.id], values, context)
        return http.local_redirect('/twitter_walls')


    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>/delete'], type='http', auth="public", website=True)
    def delete_twitter_wall(self, wall, **kw):
        request.registry.get('website.twitter.wall').unlink(request.cr, SUPERUSER_ID, [wall.id], request.context)
        return http.local_redirect("/twitter_walls",query=request.params)
    

    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>/archieve'], type='http', auth="public", website=True)
    def twitter_wall_approve(self, wall, **kw):
        vals = { 'wall' : wall}
        return request.website.render("website_twitter_wall.twitter_wall_archieve", vals)


    @http.route('/twitter_wall/pull_tweet/<model("website.twitter.wall"):wall>', type='json', auth="public", website=True)
    def tweet_data(self, wall, last_tweet=None):
        tweet = False

        domain = [('wall_id', '=', wall.id)]

        if last_tweet:
            domain += [('id','>',last_tweet)]

        website_twitter_tweet = request.registry.get('website.twitter.wall.tweet')
        tweets = website_twitter_tweet.search_read(request.cr, SUPERUSER_ID, domain, [], 0, limit=1, order='id desc', context=request.context)

        if tweets and tweets[-1].get('id') != last_tweet:
            tweet = tweets[-1]

        return tweet