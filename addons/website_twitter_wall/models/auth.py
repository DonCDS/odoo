import thread, ssl, json, urllib, urllib2, logging, httplib

from urllib import urlencode
from urllib2 import urlopen, Request, quote
from threading import Thread
from time import sleep
from socket import timeout
from oauth.oauth import OAuthRequest, OAuthConsumer, OAuthSignatureMethod_HMAC_SHA1, OAuthToken
from openerp.osv import osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

STREAM_VERSION = '1.1'

TWITTER_API_KEY = 'mQP4B4GIFo0bjGW4VB1wMxNJ3'
TWITTER_API_SECRET = 'XrRKiqONjENN55PMW8xxPx8XOL6eKitt53Ks8OS9oeEZD9aEBf'

class AuthToken(object):
    def __init__(self, key, secret):
        self.key, self.secret = key, secret
        self.callback = None

class Auth(object):
    def __init__(self, auth_token=None):
        self.REQUEST_URL = 'https://api.twitter.com/oauth/request_token'
        self.AUTHORIZE_URL = 'https://api.twitter.com/oauth/authorize'
        self.ACCESS_URL = 'https://api.twitter.com/oauth/access_token'
        self.credential_url="https://api.twitter.com/1.1/account/verify_credentials.json"

        self.auth_token = auth_token
        self.consumer = OAuthConsumer(TWITTER_API_KEY, TWITTER_API_SECRET)
        self.auth_request = None

    def request(self, url, callback=None, verifier=None, request_token=None):
        self.auth_request = OAuthRequest.from_consumer_and_token(self.consumer, token=self.auth_token or request_token, callback=callback, verifier=verifier, http_url=url)
        signature_method = OAuthSignatureMethod_HMAC_SHA1()
        self.auth_request.sign_request(signature_method, self.consumer, request_token)
        return self.auth_request

    def get_authorise_user_id(self):
        auth_req = self.request(self.credential_url, request_token=self.auth_token)
        req = Request(self.credential_url + '?' + auth_req.to_postdata())
        response = urlopen(req).read()
        return json.loads(response)['id_str']

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
        auth_req = self.auth.request(url.split('?')[0], request_token=self.auth.auth_token)
        print '----HEADERS',auth_req.to_header()
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
                self.headers['Authorization'] = auth_req.to_header()['Authorization']
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
            print '------exception',exception
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

class WallListener(object):
    
    def __init__(self, base_url, wall):
        super(WallListener, self).__init__()
        self.wall = wall
        self.base_url = base_url

    def on_connect(self):
        _logger.info('StreamListener Connect to Twitter API for wall: %s', self.wall.name)
        return True

    def on_data(self, data):
        import urllib2
        import urllib
        tweet = json.loads(data)
        params = {
            'params':tweet
        }
        url = "%s/%s/%s" % (self.base_url, 'twitter_wall/push_tweet', self.wall.id)
        req = urllib2.Request(url, json.dumps(params), {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)
        return True
    
    def on_status(self, status):
        return 

    def on_error(self, status):
        raise osv.except_osv(_('Error!'), _('StreamListener has error :%s.') % (status))
        return False

    def on_timeout(self):
        return

    def on_disconnect(self, notice):
        return False