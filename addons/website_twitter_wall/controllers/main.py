import openerp
import ast, base64
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website as controllers
from openerp import SUPERUSER_ID
from datetime import datetime
from oauth import oauth
from openerp.addons.web.controllers.main import login_redirect, ensure_db

class website_twitter_wall(http.Controller):
    
    @http.route(['/create_twitter_wall'], type='http', auth="public", website=True)
    def create_twitter_wall(self, wall_name= None, screen_name=None, include_retweet=False, wall_description=None, **kw):
        if screen_name: screen_name_id = request.registry.get('website.twitter.screen.name').create(request.cr, SUPERUSER_ID, {'name':screen_name}, request.context)
        values = {
            'name': wall_name,
            'note': wall_description,
            're_tweet':include_retweet,
        }
        wall_id = request.registry.get('website.twitter.wall').create(request.cr, SUPERUSER_ID, values, request.context)
        if screen_name: request.cr.execute("insert into rel_wall_screen_name values('%s','%s')" % (wall_id, screen_name_id))
        return http.local_redirect("/twitter_walls",query=request.params)
    
    @http.route(['/twitter_walls',
                '/twitter_wall/<model("website.twitter.wall"):wall>'], type='http', auth="public", website=True)
    def twitter_wall(self, wall=None, **kw):
        wall_obj = request.registry.get('website.twitter.wall')
        if wall:
            for walls in wall_obj.browse(request.cr, SUPERUSER_ID, [wall.id], context=request.context):
                vals = {
                    'wall_id' : wall.id,
                    'uid':request.session.uid or False,
                    'view_mode' : wall.view_mode
                }
            return request.website.render("website_twitter_wall.twitter_wall", vals)
        
        wall_ids = wall_obj.search(request.cr, SUPERUSER_ID, [], context=request.context)
        walls = wall_obj.browse(request.cr, SUPERUSER_ID, wall_ids, context=request.context)
        values={}
        for wall in walls:
            values = {
                'walls': walls
            }
        website_obj = request.registry.get('website')
        website_id = website_obj.search(request.cr, SUPERUSER_ID, [], context=request.context)[0]
        website = website_obj.browse(request.cr, openerp.SUPERUSER_ID, website_id, context=request.context)
        values.update({
               'api_conf': True if(website.twitter_api_key and website.twitter_api_secret) else False,
               'api_token_conf': True if(website.twitter_access_token and website.twitter_access_token_secret) else False
                       })
        return request.website.render("website_twitter_wall.twitter_walls", values)
    
    @http.route(['/twitter_wall/authenticate'], type='http', auth="public", website=True)
    def authenticate_twitter_wall(self, **kw):
        website_obj = request.registry.get('website')
        website_id = website_obj.search(request.cr, SUPERUSER_ID, [], context=request.context)[0]
        website = website_obj.browse(request.cr, openerp.SUPERUSER_ID, website_id, context=request.context)
        auth = oauth(website.twitter_api_key, website.twitter_api_secret)
        base_url = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID, 'web.base.url')
        auth._request_token(base_url, request.cr.dbname, website_id)
        return http.local_redirect("/twitter_walls",query=request.params)
    
    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>/delete'], type='http', auth="public", website=True)
    def delete_twitter_wall(self, wall, **kw):
        request.registry.get('website.twitter.wall').unlink(request.cr, SUPERUSER_ID, [wall.id], request.context)
        return http.local_redirect("/twitter_walls",query=request.params)
    
    @http.route(['/twitter_wall/<model("website.twitter.wall"):wall>/archieve'], type='http', auth="public", website=True)
    def twitter_wall_approve(self, wall, **kw):
        vals = { 'wall' : wall}
        return request.website.render("website_twitter_wall.twitter_wall_archieve", vals)

    @http.route('/twitter_wall_tweet_data', type='json', auth="public", website=True)
    def tweet_data(self, wall_id, published_date = None, limit = None, fetch_all = False, order = None, last_tweet = None):
        search_filter = [('wall_id', '=', wall_id)]
        if not fetch_all and published_date:
            search_filter.append(('published_date', '>', published_date))
        if last_tweet:
            search_filter.append(('id', '<', last_tweet))
        if limit:
            order="id desc"
        website_twitter_tweet = request.registry.get('website.twitter.wall.tweet')
        tweets = website_twitter_tweet.search_read(request.cr, SUPERUSER_ID, search_filter, [], 0, limit, order, context=request.context)
        data = []
        for tweet in tweets:
            #fetch date from tweet and show in this format
            created_at_date = datetime.strptime(tweet['created_at'], "%Y-%m-%d %H:%M:%S")
            tweet.update({"created_at_formated_date" : created_at_date.strftime("%d %b %Y %H:%M:%S")})
            media_list = []
            for media_ids in tweet['tweet_media_ids']:
                tweet_medias = request.registry.get('website.twitter.tweet.media').search_read(request.cr, SUPERUSER_ID, [('id', '=', media_ids)], context=request.context)
                media_list += [tweet_media for tweet_media in tweet_medias]
            tweet['tweet_media_ids'] = media_list
            data.append(tweet)
        return data

    @http.route('/tweet_moderate/streaming', type='json')
    def twitter_moderate_streaming(self, wall_id, state):
        registry, cr, context = request.registry, request.cr, request.context
        wall_obj = registry.get('website.twitter.wall')
        if state == 'startstreaming': wall_obj.start_incoming_tweets(cr, SUPERUSER_ID, [wall_id], context=context)
        if state == 'stopstreaming': wall_obj.stop_incoming_tweets(cr, SUPERUSER_ID, [wall_id], context=context)
        return state
    
    @http.route('/tweet_moderate/view_mode', type='json')
    def twitter_moderate_view_mode(self, wall_id, view_mode):
        registry, cr, context = request.registry, request.cr, request.context
        wall_obj = registry.get('website.twitter.wall')
        wall_obj.write(request.cr, SUPERUSER_ID, [wall_id], { 'view_mode': view_mode }, request.context)
    
    @http.route('/twitter_callback', type='http', auth="none")
    def twitter_callback(self, **kw):
        if not request.session.uid:
            request.params['redirect']='/twitter_callback?'+request.httprequest.query_string
            return login_redirect()
        
        website_id = int(request.params['website_id'])
        website_ids = request.registry.get("website").search(request.cr, openerp.SUPERUSER_ID, [('id','=',website_id)])
        website = request.registry.get("website").browse(request.cr, openerp.SUPERUSER_ID, website_ids, context=request.context)

        for web in website:
            access_token_response = oauth._access_token(oauth(web.twitter_api_key,web.twitter_api_secret), request.params['oauth_token'], request.params['oauth_verifier'])
            vals= {
               'twitter_access_token' : access_token_response['oauth_token'],
               'twitter_access_token_secret' : access_token_response['oauth_token_secret']
            }
            request.registry.get("website").write(request.cr, openerp.SUPERUSER_ID, website_id, vals, context=request.context)

        return http.local_redirect("/twitter_walls",query=request.params)
