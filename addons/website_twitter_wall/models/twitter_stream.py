import json
import thread

import random
import hmac
# import time

import ssl
# import base64
import httplib

# import lxml.html
# from hashlib import sha1

from time import sleep
from socket import timeout
from threading import Thread

import openerp.modules.registry
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.addons.website_twitter_wall.controllers.oauth import oauth

from urllib2 import urlopen, Request, HTTPError, quote

import logging
_logger = logging.getLogger(__name__)

STREAM_VERSION = '1.1'

stream_obj={}

class StreamListener(object):

    def __init__(self, api=None):
        pass

    def on_connect(self):
        """Called once connected to streaming server.

        This will be invoked once a successful response
        is received from the server. Allows the listener
        to perform some work prior to entering the read loop.
        """
        pass

    def on_data(self, raw_data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """
        data = json.loads(raw_data)

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_exception(self, exception):
        """Called when an unhandled exception occurs."""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_event(self, status):
        """Called when a new event arrives"""
        return

    def on_direct_message(self, status):
        """Called when a new direct message arrives"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return

    def on_disconnect(self, notice):
        """Called when twitter sends a disconnect notice
        Disconnect codes are listed here:
        https://dev.twitter.com/docs/streaming-apis/messages#Disconnect_messages_disconnect
        """
        return

class Stream(object):
    
    host = 'stream.twitter.com'

    def __init__(self, auth, listener, **options):
        self.auth = auth
        self.listener = listener
        self.running = False
        self.timeout = options.get("timeout", 300.0)
        self.retry_count = options.get("retry_count")
        self.retry_time_start = options.get("retry_time", 5.0)
        self.retry_420_start = options.get("retry_420", 60.0)
        self.retry_time_cap = options.get("retry_time_cap", 320.0)
        self.snooze_time_step = options.get("snooze_time", 0.25)
        self.snooze_time_cap = options.get("snooze_time_cap", 16)
        self.buffer_size = options.get("buffer_size",  1500)
        if options.get("secure", True):
            self.scheme = "https"
        else:
            self.scheme = "http"

        self.headers = options.get("headers") or {}
        self.parameters = None
        self.body = None
        self.retry_time = self.retry_time_start
        self.snooze_time = self.snooze_time_step

    def _run(self):
        # Authenticate
        url = "%s://%s%s" % (self.scheme, self.host, self.url)

        # Connect and process the stream
        error_counter = 0
        conn = None
        exception = None
        while self.running:
            if self.retry_count is not None and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                if self.scheme == "http":
                    conn = httplib.HTTPConnection(self.host, timeout=self.timeout)
                else:
                    conn = httplib.HTTPSConnection(self.host, timeout=self.timeout)
                self.headers['Authorization'] = str(self.auth._generate_header(url.split('?')[0], 'HMAC-SHA1', '1.0', params=self.parameters))
                conn.connect()
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    if resp.status == 420:
                        self.retry_time = max(self.retry_420_start, self.retry_time)
                    sleep(self.retry_time)
                    self.retry_time = min(self.retry_time * 2, self.retry_time_cap)
                else:
                    error_counter = 0
                    self.retry_time = self.retry_time_start
                    self.snooze_time = self.snooze_time_step
                    self.listener.on_connect()
                    self._read_loop(resp)
            except (timeout, ssl.SSLError) as exc:
                # If it's not time out treat it like any other exception
                if isinstance(exc, ssl.SSLError) and not (exc.args and 'timed out' in str(exc.args[0])):
                    exception = exc
                    break

                if self.listener.on_timeout() == False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
                self.snooze_time = min(self.snooze_time + self.snooze_time_step,
                                       self.snooze_time_cap)
            except Exception as exception:
                # any other exception is fatal, so kill loop
                break
        # cleanup
        self.running = False
        if not self.running:
            self.listener.on_disconnect(None)
        if conn:
            conn.close()

        if exception:
            # call a handler first so that the exception can be logged.
            self.listener.on_exception(exception)
            raise

    def _data(self, data):
        if self.listener.on_data(data) is False:
            self.running = False

    def _read_loop(self, resp):

        while self.running and not resp.isclosed():
            # Note: keep-alive newlines might be inserted before each length value.
            # read until we get a digit...
            c = '\n'
            while c == '\n' and self.running and not resp.isclosed():
                c = resp.read(1)
            delimited_string = c

            # read rest of delimiter length..
            d = ''
            while d != '\n' and self.running and not resp.isclosed():
                d = resp.read(1)
                delimited_string += d

            # read the next twitter status object
            if delimited_string.strip().isdigit():
                next_status_obj = resp.read( int(delimited_string) )
                if self.running:
                    self._data(next_status_obj)

        if resp.isclosed():
            self.on_closed(resp)

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def on_closed(self, resp):
        """ Called when the response has been closed by Twitter """
        pass

    def filter(self, follow=None, track=None, async=False, locations=None, stall_warnings=False, languages=None, encoding='utf8'):
        self.parameters = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            _logger.error('Stream object already connected!')
        self.url = '/%s/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            encoded_follow = [s.encode(encoding) for s in follow]
            self.parameters['follow'] = ','.join(encoded_follow)
        if track:
            encoded_track = [s.encode(encoding) for s in track]
            self.parameters['track'] = ','.join(encoded_track)
        if locations and len(locations) > 0:
            assert len(locations) % 4 == 0
            self.parameters['locations'] = ','.join(['%.4f' % l for l in locations])
        if stall_warnings:
            self.parameters['stall_warnings'] = stall_warnings
        if languages:
            self.parameters['language'] = ','.join(map(str, languages))
        self.body = '&'.join(['%s=%s' % (quote(str(k), ''), quote(str(v), '')) for k, v in self.parameters.iteritems()])
        self.parameters['delimited'] = 'length'
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.listener.on_disconnect(None)
        self.running = False

class WallManager(object):

    def __init__(self, dbname, ids, wall):
        self.registry = openerp.modules.registry.RegistryManager.get(dbname)
        self.wall = wall
        self.ids = ids
    
    def start(self):
        def func(user_ids):
            return stream.filter(follow=user_ids)
        
        if (self.wall.state != 'not_streaming'):
            return False
        if (self.check_api_token()):
            listner = WallListener(self.registry, self.wall.id, self.wall.name)
            auth = oauth(self.wall.website_id.twitter_api_key, self.wall.website_id.twitter_api_secret)
            #OAuthHandler oauth
            if(self.check_access_token()):
                auth.set_access_token(self.wall.website_id.twitter_access_token, self.wall.website_id.twitter_access_token_secret)
                stream = Stream(auth, listner)
                if self.wall.id not in stream_obj:
                    stream_obj.update({self.wall.id : []})
                stream_obj[self.wall.id].append(stream)
                user_ids = [auth.get_user_id(screen_name.name) for screen_name in self.wall.screen_name]
                user_ids.append(auth.get_authorise_user_id())
                thread.start_new_thread(func, (user_ids, ))
                return True
        else:
            _logger.error('Contact System Administration for Configure Twitter API KEY and ACCESS TOKEN.')
            raise osv.except_osv(_('Error Configuration!'), _('Contact System Administration for Configure Twitter API KEY and ACCESS TOKEN.')) 
            return False
    
    def check_api_token(self):
        website = self.wall.website_id
        if(website.twitter_api_key and website.twitter_api_secret):
            return True
        else:
            return False
    
    def check_access_token(self):
        website = self.wall.website_id
        if(website.twitter_access_token and website.twitter_access_token_secret):
            return True
        else:
            o_auth = oauth(self.wall.website_id.twitter_api_key, self.wall.website_id.twitter_api_secret)
            with self.registry.cursor() as cr:
                base_url = self.registry.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url')
                return o_auth._request_token(base_url, cr.dbname, self.wall.website_id.id)

class WallListener(StreamListener):
    
    def __init__(self, registry, wall_id, wall_name):
        super(WallListener, self).__init__()
        self.wall_id = wall_id
        self.registry = registry
        self.wall_name = wall_name
        
    def on_connect(self):
        _logger.info('StreamListener Connect to Twitter API for wall: %s - %s ', self.wall_name, self.wall_id)
        return True

    def on_data(self, data):
        wall_obj = self.registry.get('website.twitter.wall')
        with self.registry.cursor() as cr:
            stream_state = wall_obj.browse(cr, openerp.SUPERUSER_ID, self.wall_id, context=None)['state']
            if stream_state != 'streaming':
                return False
            tweet = self._process_tweet(json.loads(data))
            if tweet:
            	wall_obj._set_tweets(cr, openerp.SUPERUSER_ID, self.wall_id, tweet, context=None)
        return True
    
    def on_status(self, status):
        _logger.info('StreamListener status for wall: %s - %s', self.wall_name, self.wall_id)
        return 

    def on_error(self, status):
        _logger.error('StreamListener has error :%s to connect with wall: %s - %s', status, self.wall_name, self.wall_id)
        raise osv.except_osv(_('Error!'), _('StreamListener has error :%s.') % (status))
        return False

    def on_timeout(self):
        _logger.warning('StreamListener timeout to connect with wall: %s - %s', self.wall_name, self.wall_id)
        return

    def on_disconnect(self, notice):
        _logger.info('StreamListener disconnect with wall: %s - %s', self.wall_name, self.wall_id)
        return False
    
    def _process_tweet(self, tweet):
        if not tweet.has_key('user'):
            return None

        wall_obj = self.registry.get('website.twitter.wall')
        with self.registry.cursor() as cr:
            walls = wall_obj.search_read(cr, openerp.SUPERUSER_ID, [('id', '=', self.wall_id)], ["re_tweet"])
            for wall in walls:
                re_tweet = wall["re_tweet"]

        if not re_tweet:
            if tweet.has_key('retweeted_status'):
                return None

        if tweet.has_key('retweeted_status'):
            tweet = tweet.get('retweeted_status')
        return tweet
