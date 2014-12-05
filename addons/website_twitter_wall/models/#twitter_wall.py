import httplib
import io
import json
import urllib
import thread
import urllib2
import datetime
import cStringIO
from PIL import *

import openerp
from openerp import api, fields, models
from openerp.osv import osv
#from twitter_stream import WallListener, Stream
#from openerp.addons.website_twitter_wall.controllers.oauth import oauth
from twitter_stream import Auth

stream_pool = {
    
}
STREAM_URL = "https://userstream.twitter.com/2/user.json"
class TwitterWall(osv.osv):
    _name = "website.twitter.wall"

    name = fields.Char(string='Wall Name')
    description = fields.Text(string='Description')
    tweet_ids = fields.One2many('website.twitter.wall.tweet', 'wall_id', string='Tweets')
    website_id = fields.Many2one('website', string='Website')
    re_tweet = fields.Boolean(string='Include Re-Tweet ?')
    number_view = fields.Integer('# of Views')
    state = fields.Selection([('not_streaming', 'Draft'), ('streaming', 'In Progress'), ('story', 'Story')],string="State")
    website_published = fields.Boolean(string='Visible in Website')
    user_id = fields.Many2one('res.users',string='Created User',default=1)
    twitter_access_token = fields.Char(string='Twitter Access Token key', help="Twitter Access Token Key")
    twitter_access_token_secret = fields.Char(string='Twitter Access Token secret', help="Twitter Access Token Secret")
    image = fields.Binary(string='Image')
    image_thumb = fields.Binary(string='Thumbnail')
    
    def get_api_keys(self):
        twitter_api_key = 'mQP4B4GIFo0bjGW4VB1wMxNJ3'
        twitter_api_secret = 'XrRKiqONjENN55PMW8xxPx8XOL6eKitt53Ks8OS9oeEZD9aEBf'
        return twitter_api_key, twitter_api_secret

    @api.multi
    def start_incoming_tweets(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        
        def func(stream, user_ids):
            return stream.filter(follow=user_ids)

        if stream_pool.get(self.id):
            return True
        
        if self.twitter_access_token and self.twitter_access_token_secret:
            twitter_api_key, twitter_api_secret = self.get_api_keys()

            #consumer = Token(twitter_api_key, twitter_api_secret)

            auth = Auth(self.twitter_access_token, self.twitter_access_token_secret)
            auth.set_parameters(auth.STREAM_URL)
            #user_ids = access_token.get_user_ids(consumer)

            auth.get_data()
            
            '''
            listner = WallListener(base_url, self)

            auth.set_access_token(self.twitter_access_token, self.twitter_access_token_secret)
            stream = stream_pool.get(self.id, False)
            if not stream:
                stream = Stream(auth, listner)
            stream_pool[self.id] = stream

            user_ids = auth.get_authorise_user_id()
            thread.start_new_thread(func, (stream, [user_ids], ))
            '''
        self.write({'state': 'streaming'})
        return True
    
    #TODO: to check, may be useful to place this image in to website module
    @api.model
    def crop_image(self, data, type='top', ratio=False, thumbnail_ratio=None, image_format="PNG"):
        """ Used for cropping image and create thumbnail
            :param data: base64 data of image.
            :param type: Used for cropping position possible
                Possible Values : 'top', 'center', 'bottom'
            :param ratio: Cropping ratio
                e.g for (4,3), (16,9), (16,10) etc
                send ratio(1,1) to generate square image
            :param thumbnail_ratio: It is size reduce ratio for thumbnail
                e.g. thumbnail_ratio=2 will reduce your 500x500 image converted in to 250x250
            :param image_format: return image format PNG,JPEG etc
        """
        
        image = Image.open(cStringIO.StringIO(data.decode('base64')))
        output = io.BytesIO()
        w, h = image.size
        new_h = h
        new_w = w

        if ratio:
            w_ratio, h_ratio = ratio
            new_h = (w * h_ratio) / w_ratio
            new_w = w
            if new_h > h:
                new_h = h
                new_w = (h * w_ratio) / h_ratio

        if type == "top":
            cropped_image = image.crop((0, 0, new_w, new_h))
            cropped_image.save(output,format=image_format)
        elif type == "center":
            cropped_image = image.crop(((w - new_w)/2, (h - new_h)/2, (w + new_w)/2, (h + new_h)/2))
            cropped_image.save(output,format=image_format)
        elif type == "bottom":
            cropped_image = image.crop((0, h - new_h, new_w, h))
            cropped_image.save(output,format=image_format)
        else:
            raise ValueError('ERROR: invalid value for crop_type')
        if thumbnail_ratio:
            thumb_image = Image.open(cStringIO.StringIO(output.getvalue()))
            thumb_image.thumbnail((new_w/thumbnail_ratio, new_h/thumbnail_ratio), Image.ANTIALIAS)
            output = io.BytesIO()
            thumb_image.save(output, image_format)
        return output.getvalue().encode('base64')

    @api.multi
    def create(self, values):
        if values.get('image'):
            image_thumb = self.crop_image(values['image'], thumbnail_ratio=4)
            image = self.crop_image(values['image'])
            values.update({
                'image_thumb': image_thumb,
                'image': image
            })
        wall_id = super(TwitterWall, self).create(values)
        return wall_id
    
    @api.model
    def get_thumb_image(self):
        return "/website/image/website.twitter.wall/%s/image_thumb" % self.id

    @api.model
    def get_image(self):
        return "/website/image/website.twitter.wall/%s/image" % self.id

    @api.multi
    def stop_incoming_tweets(self):
        for wall in self:
            stream_pool.get(wall).disconnect()
        self.write({'state': 'not_streaming'})
        return True

    @api.multi
    def create_tweets(self, vals):
        Tweet = self.env['website.twitter.wall.tweet']
        tweet_val = Tweet._process_tweet(self.id, vals)
        tweet_id = Tweet.create(tweet_val)
        return tweet_id

class WebsiteTwitterTweet(osv.osv):
    _name = "website.twitter.wall.tweet"

    wall_id = fields.Many2one('website.twitter.wall',string='Wall')
    html_description = fields.Html(string='Tweet')
    tweet_id = fields.Char(string='Tweet Id', size=256)
    tweet_json = fields.Text(string='Tweet Json Data')
    published_date = fields.Datetime(string='Publish on')

    _sql_constraints = [
        ('tweet_uniq', 'unique (wall_id, tweet_id)', 'Duplicate tweet in wall is not allowed !')
    ]

    @api.model
    def _process_tweet(self, wall_id, tweet):        
        card_url = "https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true" % (tweet.get('id'))
        req = urllib2.Request(card_url, None, {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)
        data = response.read()
        cardtweet = json.loads(data)


        vals = {
            'html_description': cardtweet.get('html', False),
            'tweet_json': json.dumps(tweet),
            'tweet_id': tweet.get('id'),
            'published_date': datetime.datetime.now(),
            'wall_id': wall_id
        }
        return vals