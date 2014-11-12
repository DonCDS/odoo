import base64
import urllib2
import mimetypes
from urllib2 import urlopen
from urllib2 import Request as URLRequest

from oauth import oauth
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request

class website_twitter_wall(http.Controller):

    _tweet_per_page = 10
    
    @http.route('/create_twitter_wall', type='http', auth='user', website=True)
    def create_twitter_wall(self, image=None, wall_name= None, screen_name=None, include_retweet=False, wall_description=None, **kw):
        values = {
            'name': wall_name,
            'description': wall_description,
            'website_id': 1,
            'state': 'not_streaming',
            'website_published': True,
            'user_id': request.uid
        }
        if 'http' in image or 'https' in image:
            mmtp = mimetypes.guess_type(image,strict=True)
            if not mmtp[0]:
                return False
            ext = mimetypes.guess_extension(mmtp[0])
            f= open("tmp"+ext,'wb')
            req = urllib2.Request(image,headers={'User-Agent': 'Mozilla/5.0'})
            f.write(urllib2.urlopen(req).read())
            f.close()
            img = open("tmp"+ext,"rb").read().encode("base64").replace("\n","")
            values['image'] = img
        else:
            values['image'] = image
        wall_id = request.env['website.twitter.wall'].create(values)
        return http.local_redirect("/twitter_walls")
    
    @http.route('/twitter_walls', type='http', auth='public', website=True)
    def twitter_walls(self):
        Wall = request.env['website.twitter.wall']
        domain = []

        if request.env.user.id == request.website.user_id.id:
            domain += [('website_published', '=', True), ('state', 'in', ['streaming', 'story'])]
            
        values = {
            'walls': Wall.search(domain).sudo(),
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        return request.website.render("website_twitter_wall.twitter_walls", values)
    

    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>'], type='http', auth="public", website=True)
    def twitter_wall(self, wall):
        Wall = request.env['website.twitter.wall']
        Wall.browse([wall.id]).start_incoming_tweets()
        values = {
            'wall_id' : wall.id,
            'uid': request.session.uid or False
        }
        return request.website.render("website_twitter_wall.twitter_wall", values)

    @http.route(['/twitter_wall/push_tweet/<model("website.twitter.wall"):wall>'], method=['POST'], type='json', auth='public', website=True)
    def push_tweet(self, wall, **args):
        request.env['website.twitter.wall'].browse([wall.id]).create_tweets(args)
        return True

    @http.route('/twitter_wall/pull_tweet/<model("website.twitter.wall"):wall>', type='json', auth="public", website=True)
    def pull_tweet(self, wall, last_tweet=None):
        tweet = False
        domain = [('wall_id', '=', wall.id)]

        if last_tweet:
            domain += [('id','>',last_tweet)]
        
        Tweet = request.env['website.twitter.wall.tweet']
        tweets = Tweet.search_read(domain, [], offset=0, limit=1, order='id desc')
        if tweets and tweets[-1].get('id') != last_tweet:
            tweet = tweets[-1]

        return tweet

    @http.route(['/twitter_wall/story/<model("website.twitter.wall"):wall>',
                '/twitter_wall/story/<model("website.twitter.wall"):wall>/page/<int:page>'], type='http', auth="public", website=True)
    def twitter_wall_archieve(self, wall, page=1):
        Wall = request.env['website.twitter.wall']
        Tweet = request.env['website.twitter.wall.tweet']
        wall_obj = Wall.browse([wall.id])
        
        if wall.state != 'story':
            wall_obj.write({'state':'story'})

        domain = [('wall_id','=',wall.id)]

        pager = request.website.pager(url="/twitter_wall/story/%s" % (wall.id), total=Tweet.search_count(domain), page=page,
                                      step=self._tweet_per_page, scope=self._tweet_per_page,
                                      url_args={})
        tweets = Tweet.search(domain, limit=self._tweet_per_page, offset=pager['offset'], order='id desc').sudo()
        values = {
            'wall' : wall,
            'tweets': tweets,
            'pager':pager,
            'is_public_user': request.env.user.id == request.website.user_id.id
        }
        if page == 1:
            wall_obj.write({'number_view':wall_obj.number_view + 1})
        
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
        Wall = request.env['website.twitter.wall']
        wall_obj = Wall.browse([wall.id])
        auth = oauth(twitter_api_key, twitter_api_secret)
        access_token_response = oauth._access_token(auth, oauth_token, oauth_verifier)
        values = {
           'twitter_access_token': access_token_response['oauth_token'],
           'twitter_access_token_secret': access_token_response['oauth_token_secret']
        }
        wall_obj.write(values)
        return http.local_redirect('/twitter_walls')


    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>/delete'], type='http', auth="public", website=True)
    def delete_twitter_wall(self, wall, **kw):
        Wall = request.env['website.twitter.wall']
        Wall.browse([wall.id]).unlink()
        return http.local_redirect("/twitter_walls",query=request.params)