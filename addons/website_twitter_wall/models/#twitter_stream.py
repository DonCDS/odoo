from oauth.oauth import OAuthRequest, OAuthSignatureMethod_HMAC_SHA1, OAuthConsumer
from hashlib import md5
from urllib import urlencode
from urllib2 import Request, urlopen
import json, time
import random, math, re, urllib, urllib2


TWITTER_API_KEY = 'mQP4B4GIFo0bjGW4VB1wMxNJ3'
TWITTER_API_SECRET = 'XrRKiqONjENN55PMW8xxPx8XOL6eKitt53Ks8OS9oeEZD9aEBf'

class Auth(object):

	def __init__(self, api_key=None, api_secret=None):
		self.STREAM_URL = "https://userstream.twitter.com/2/user.json"
		self.REQUEST_URL = "https://api.twitter.com/oauth/request_token"
		self.AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
		self.ACCESS_URL = "https://api.twitter.com/oauth/access_token"
		self.key, self.secret = api_key, api_secret
		self.consumer = OAuthConsumer(TWITTER_API_KEY,TWITTER_API_SECRET)
		self.auth_request = None
		self.parameters = {}

	def _generate_nonce(self):
		random_number = ''.join(str(random.randint(0, 9)) for i in range(40))
		m = md5(str(time.time()) + str(random_number))
		return m.hexdigest()

	def set_parameters(self, url, callback=None, token=None):
		self.parameters = {
			'oauth_consumer_key': self.consumer.key,
			'oauth_token': self.key,
			'oauth_signature_method': 'HMAC-SHA1',
			'oauth_timestamp': str(int(time.time())),
			'oauth_nonce': self._generate_nonce(),
			'oauth_version': '1.0',
			}
		self.auth_request = OAuthRequest.from_token_and_callback(self,http_url=url,parameters=self.parameters)
		signature_method = OAuthSignatureMethod_HMAC_SHA1()
		self.parameters['oauth_signature'] = signature_method.build_signature(self.auth_request,self.consumer,self)
		return self.parameters

	def get_data(self):
		request = Request(self.STREAM_URL)
		request.add_header('Authorization',self.auth_request.to_header()['Authorization'])
		resp = urllib2.urlopen(request)
		#resp = urllib2.urlopen("%s?%s" % (self.STREAM_URL,urllib.urlencode(self.parameters)))
		raise Exception(resp)