# -*- coding: utf-8 -*-

import openerp
from openerp.http import request
from openerp import models, api, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from datetime import datetime
import werkzeug.urls
import urllib2
import simplejson

import logging
_logger = logging.getLogger(__name__)


class google_service(models.TransientModel):
    _name = 'google.service'

    @api.model
    def generate_refresh_token(self, service, authorization_code):
        ir_config = self.env['ir.config_parameter']
        client_id = ir_config.sudo().get_param('google_%s_client_id' % service)
        client_secret = ir_config.sudo().get_param('google_%s_client_secret' % service)
        redirect_uri = ir_config.sudo().get_param('google_redirect_uri')

        #Get the Refresh Token From Google And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = dict(code=authorization_code, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, grant_type="authorization_code")
        data = werkzeug.url_encode(data)
        try:
            req = urllib2.Request("https://accounts.google.com/o/oauth2/token", data, headers)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            error_msg = "Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired"
            raise self.env['res.config.settings'].get_config_warning(_(error_msg))

        content = simplejson.loads(content)
        return content.get('refresh_token')

    @api.model
    def _get_google_token_uri(self, service, scope):
        ir_config = self.env['ir.config_parameter']
        params = {
            'scope': scope,
            'redirect_uri': ir_config.sudo().get_param('google_redirect_uri'),
            'client_id': ir_config.sudo().get_param('google_%s_client_id' % service),
            'response_type': 'code',
            'client_id': ir_config.sudo().get_param('google_%s_client_id' % service),
        }
        uri = 'https://accounts.google.com/o/oauth2/auth?%s' % werkzeug.url_encode(params)
        return uri

    # If no scope is passed, we use service by default to get a default scope
    @api.model
    def _get_authorize_uri(self,from_url, service, scope=False):
        """ This method return the url needed to allow this instance of OpenErp to access to the scope of gmail specified as parameters """
        state_obj = dict(d=self._cr.dbname, s=service, f=from_url)

        base_url = self.get_base_url()
        client_id = self.get_client_id(service)

        params = {
            'response_type': 'code',
            'client_id': client_id,
            'state': simplejson.dumps(state_obj),
            'scope': scope or 'https://www.googleapis.com/auth/%s' % (service,),
            'redirect_uri': base_url + '/google_account/authentication',
            'approval_prompt': 'force',
            'access_type': 'offline'
        }

        uri = self.get_uri_oauth(a='auth') + "?%s" % werkzeug.url_encode(params)
        return uri

    @api.model
    def _get_google_token_json(self, authorize_code, service):
        res = False
        base_url = self.get_base_url()
        client_id = self.get_client_id(service)
        client_secret = self.get_client_secret(service)

        params = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_account/authentication'
        }

        headers = {"content-type": "application/x-www-form-urlencoded"}

        try:
            uri = self.get_uri_oauth(a='token')
            data = werkzeug.url_encode(params)

            st, res, ask_time = self._do_request(uri, params=data, headers=headers, type='POST', preuri='')
        except urllib2.HTTPError:
            error_msg = "Something went wrong during your token generation. Maybe your Authorization Code is invalid"
            raise self.env['res.config.settings'].get_config_warning(_(error_msg))
        return res

    @api.model
    def _refresh_google_token_json(self, refresh_token, service):  # exchange_AUTHORIZATION vs Token (service = calendar)
        res = False
        client_id = self.get_client_id(service)
        client_secret = self.get_client_secret(service)

        params = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
        }

        headers = {"content-type": "application/x-www-form-urlencoded"}

        try:
            uri = self.get_uri_oauth(a='token')

            data = werkzeug.url_encode(params)
            st, res, ask_time = self._do_request(uri, params=data, headers=headers, type='POST', preuri='')
        except urllib2.HTTPError, e:
            if e.code == 400:  # invalid grant
                registry = openerp.modules.registry.RegistryManager.get(request.session.db)
                with registry.cursor() as cur:
                    self.env['res.users'].write([self.uid], {'google_%s_rtoken' % service: False})
            error_key = simplejson.loads(e.read()).get("error", "nc")
            _logger.exception("Bad google request : %s !" % error_key)
            error_msg = "Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired [%s]" % error_key
            raise self.env['res.config.settings'].get_config_warning(_(error_msg))
        return res

    @api.model
    def _do_request(self, uri, params={}, headers={}, type='POST', preuri="https://www.googleapis.com"):
        if context is None:
            context = {}

        """ Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE') """
        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !" % (uri, type, headers, werkzeug.url_encode(params) if type == 'GET' else params))

        status = 418
        response = ""
        try:
            if type.upper() == 'GET' or type.upper() == 'DELETE':
                data = werkzeug.url_encode(params)
                req = urllib2.Request(preuri + uri + "?" + data)
            elif type.upper() == 'POST' or type.upper() == 'PATCH' or type.upper() == 'PUT':
                req = urllib2.Request(preuri + uri, params, headers)
            else:
                raise ('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!' % (type))
            req.get_method = lambda: type.upper()

            request = urllib2.urlopen(req)
            status = request.getcode()

            if int(status) in (204, 404):  # Page not found, no response
                response = False
            else:
                content = request.read()
                response = simplejson.loads(content)

            try:
                ask_time = datetime.strptime(request.headers.get('date'), "%a, %d %b %Y %H:%M:%S %Z")
            except:
                ask_time = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        except urllib2.HTTPError, e:
            if e.code in (400, 401, 410):
                raise e

            _logger.exception("Bad google request : %s !" % e.read())
            raise self.env['res.config.settings'].get_config_warning(_("Something went wrong with your request to google"))
        return (status, response, ask_time)

    @api.model
    def get_base_url(self):
        return self.env['ir.config_parameter'].get_param('web.base.url', default='http://www.openerp.com?NoBaseUrl')

    @api.model
    def get_client_id(self, service):
        return self.env['ir.config_parameter'].sudo().get_param('google_%s_client_id' % (service,), default=False)

    @api.model
    def get_client_secret(self, service):
        return self.env['ir.config_parameter'].sudo().get_param('google_%s_client_secret' % (service,), default=False)

    def get_uri_oauth(self, a=''):  # a = optional action
        return "https://accounts.google.com/o/oauth2/%s" % (a,)

    def get_uri_api(self):
        return 'https://www.googleapis.com'
