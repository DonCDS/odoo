from json import loads
from thread import start_new_thread
from urllib2 import urlopen, Request
from base_stream import Stream, StreamListener
from openerp import api, fields, models, SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from oauth import oauth


class TwitterConsumer(http.Controller):
    tweets = {}

    def temp(self, tweet):
        self.tweets[tweet['id_str']] = tweet

    @http.route('/twitter_wall/consume/<model("twitter.stream"):stream>/<token>', type='json', auth='public')
    def consume(self, stream, token):
        tweet = self.tweets[token]
        # If two or more wall with same twitter account are verify, than tweet is store into wall which is last create
        obj = stream.agent_ids.filtered(lambda o: o.auth_user == tweet['user']['id_str']).sorted(lambda r: r.create_date, reverse=True)
        if len(obj):
            request.env['twitter.tweet']._process_tweet(obj[0], tweet)


class TwitterStream(models.Model, StreamListener):
    _name = "twitter.stream"

    streams_objs = {}
    tc = TwitterConsumer()

    twitter_api_key = fields.Char("Twitter API Key")
    twitter_api_secret = fields.Char("Twitter API Secret Key")
    model = fields.Char("Type of Model")
    agent_ids = fields.One2many('stream.agent', 'stream_id')

    # Start streaming on server start
    def _register_hook(self, cr):
        super(TwitterStream, self)._register_hook(cr)
        self.start(cr)

    # Start streaming
    def start(self, cr):
        if not hasattr(self, '_id'):
            stream_id = self.search(cr, SUPERUSER_ID, [], limit=1)
            for stream in self.browse(cr, SUPERUSER_ID, stream_id):
                stream.start_streaming()

    @api.one
    def start_streaming(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        self = self.with_context(base_url=base_url)
        if self.agent_ids:
            def func(stream, user_ids):
                return stream.filter(follow=user_ids)
            auth = oauth(self.twitter_api_key, self.twitter_api_secret)
            stream = None
            user_ids = []
            for agent in self.agent_ids:
                if agent['auth_user']:
                    auth.set_access_token(agent['twitter_access_token'], agent['twitter_access_token_secret'])
                    stream = Stream(auth, self)
                    user_ids.append(agent['auth_user'])
            if user_ids:
                self.streams_objs[self.id] = stream
                start_new_thread(func, (stream, user_ids))
            return True

    # Stop streaming
    def stop(self):
        if self.streams_objs.get(self.id):
            self.streams_objs[self.id].disconnect()

    # Restart streaming
    def restart(self):
        self.stop()
        self.start()

    # Call when tweet is come
    def on_data(self, tweet):
        if 'delete' not in tweet:
            tweet = loads(tweet)
            self.tc.temp(tweet)
            url = "%s/%s/%s/%s" % (self._context.get('base_url'), 'twitter_wall/consume', self.id, tweet['id_str'])
            urlopen(Request(url, '{}', {'Content-Type': 'application/json'}))
        return True


class StreamAgent(models.Model):
    _name = "stream.agent"

    twitter_access_token = fields.Char('Twitter Access Token Key')
    twitter_access_token_secret = fields.Char('Twitter Access Token Secret')
    auth_user = fields.Char('Authenticated User Id')
    stream_id = fields.Many2one('twitter.stream', 'Stream Id')
    tweet_ids = fields.One2many('twitter.tweet', 'agent_id', 'Tweets')

    # Override unlink method to restart streaming when deletion perform
    @api.one
    def unlink(self):
        auth_user, stream = self.auth_user, self.stream_id
        super(StreamAgent, self).unlink()
        if auth_user:
            stream.restart()


# Store tweet
class TwitterTweet(models.Model):
    _name = "twitter.tweet"

    tweet_id = fields.Char('Tweet Id')
    html_description = fields.Html('Tweet')
    comment = fields.Html("Comment on Tweet", default="<br/>")
    agent_id = fields.Many2one('stream.agent', 'Agent Id')

    @api.model
    def _process_tweet(self, obj, tweet):
        card_url = "https://api.twitter.com/1/statuses/oembed.json?id=%s&omit_script=true" % (tweet.get('id'))
        cardtweet = loads(urlopen(Request(card_url, None, {'Content-Type': 'application/json'})).read())
        return self.create({
            'tweet_id': tweet.get('id'),
            'html_description': cardtweet.get('html', False),
            'agent_id': obj.id
        })
