import json
import thread
from urllib2 import urlopen, Request
import datetime
from PIL import *
from openerp import api, fields, models
from twitter_stream import WallListener, Stream
from openerp.addons.website_twitter_wall.controllers.oauth import oauth

stream_pool = {}


class TwitterWall(models.Model):
    _name = "website.twitter.wall"

    name = fields.Char(string='Wall Name')
    description = fields.Text(string='Description')
    tweet_ids = fields.One2many('website.twitter.wall.tweet', 'wall_id', string='Tweets')
    website_id = fields.Many2one('website', string='Website')
    number_view = fields.Integer('# of Views')
    state = fields.Selection([('not_streaming', 'Draft'), ('streaming', 'In Progress'), ('story', 'Story')], string="State")
    website_published = fields.Boolean(string='Visible in Website')
    user_id = fields.Many2one('res.users', string='Created User')
    twitter_access_token = fields.Char(string='Twitter Access Token key', help="Twitter Access Token Key")
    twitter_access_token_secret = fields.Char(string='Twitter Access Token secret', help="Twitter Access Token Secret")
    image = fields.Binary(string='Image')
    auth_user = fields.Char(string='Authenticated User id')

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

        user_ids = []
        twitter_api_key, twitter_api_secret = self.get_api_keys()
        auth = oauth(twitter_api_key, twitter_api_secret)
        for o in self.env['website.twitter.wall'].search([]):
            if o.twitter_access_token and o.twitter_access_token_secret:
                stream = stream_pool.get(o.id, False)
                if not stream:
                    listner = WallListener(base_url, self)
                    auth.set_access_token(o.twitter_access_token, o.twitter_access_token_secret)
                    stream = Stream(auth, listner)
                    o.state = 'streaming'
                stream_pool[o.id] = stream
                user_ids.append(o.auth_user)
        thread.start_new_thread(func, (stream, user_ids, ))
        return True

    @api.multi
    def create(self, values):
        if values.get('image'):
            values.update({
                'image': values['image']
            })
        wall_id = super(TwitterWall, self).create(values)
        return wall_id

    @api.multi
    def stop_incoming_tweets(self):
        if stream_pool.get(self.id):
            stream_pool.get(self.id).disconnect()
        for o in self.env['website.twitter.wall'].search([]):
            o.state = 'not_streaming'
        return True

    @api.multi
    def create_tweets(self, vals):
        tweet_obj = self.env['website.twitter.wall.tweet']
        tweet_val = tweet_obj._process_tweet(self.id, vals)
        tweet_id = tweet_obj.create(tweet_val)
        return tweet_id


class WebsiteTwitterTweet(models.Model):
    _name = "website.twitter.wall.tweet"

    wall_id = fields.Many2one('website.twitter.wall', string='Wall')
    html_description = fields.Html(string='Tweet')
    tweet_id = fields.Char(string='Tweet Id', size=256)
    tweet_json = fields.Text(string='Tweet Json Data')
    published_date = fields.Datetime(string='Publish on')

    _sql_constraints = [
        ('tweet_uniq', 'unique(wall_id, tweet_id)', 'Duplicate tweet in wall is not allowed !')
    ]

    @api.model
    def _process_tweet(self, wall_id, tweet):
        card_url = "https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true" % (tweet.get('id'))
        cardtweet = json.loads(urlopen(Request(card_url, None, {'Content-Type': 'application/json'})).read())
        vals = {
            'html_description': cardtweet.get('html', False),
            'tweet_json': json.dumps(tweet),
            'tweet_id': tweet.get('id'),
            'published_date': datetime.datetime.now(),
            'wall_id': wall_id
        }
        return vals
