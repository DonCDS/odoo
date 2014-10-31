# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""

WSGI stack, common code.

"""

import xmlrpclib

import logging
import sys
import threading
import traceback

import werkzeug.serving
import werkzeug.contrib.fixers

import openerp
import openerp.exceptions
import openerp.osv.orm
import openerp.tools.config as config

_logger = logging.getLogger(__name__)

# XML-RPC fault codes. Some care must be taken when changing these: the
# constants are also defined client-side and must remain in sync.
# User code must use the exceptions defined in ``openerp.exceptions`` (not
# create directly ``xmlrpclib.Fault`` objects).
RPC_FAULT_CODE_CLIENT_ERROR = 1 # indistinguishable from app. error.
RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

def xmlrpc_return(start_response, service, method, params, string_faultcode=False):
    """
    Helper to call a service's method with some params, using a wsgi-supplied
    ``start_response`` callback.

    This is the place to look at to see the mapping between core exceptions
    and XML-RPC fault codes.
    """
    # Map OpenERP core exceptions to XML-RPC fault codes. Specific exceptions
    # defined in ``openerp.exceptions`` are mapped to specific fault codes;
    # all the other exceptions are mapped to the generic
    # RPC_FAULT_CODE_APPLICATION_ERROR value.
    # This also mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for
    # exception handling.
    try:
        result = openerp.http.dispatch_rpc(service, method, params)
        response = xmlrpclib.dumps((result,), methodresponse=True)
    except Exception, e:
        if string_faultcode:
            response = xmlrpc_convert_exception_stringcode(e)
        else:
            response = xmlrpc_convert_exception(e)
    start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
    return [response]

def xmlrpc_convert_exception(e):
    if isinstance(e, openerp.osv.orm.except_orm): # legacy
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, openerp.tools.ustr(e.value))
    elif isinstance(e, (openerp.exceptions.Warning, openerp.exceptions.RedirectWarning)):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, str(e))
    elif isinstance (e, openerp.exceptions.AccessError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_ERROR, str(e))
    elif isinstance(e, openerp.exceptions.AccessDenied):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
    elif isinstance(e, openerp.exceptions.DeferredException):
        info = e.traceback
        # Which one is the best ?
        formatted_info = "".join(traceback.format_exception(*info))
        #formatted_info = openerp.tools.exception_to_unicode(e) + '\n' + info
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)
    else:
        if hasattr(e, 'message') and e.message == 'AccessDenied': # legacy
            fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
        else:
            info = sys.exc_info()
            # Which one is the best ?
            formatted_info = "".join(traceback.format_exception(*info))
            #formatted_info = openerp.tools.exception_to_unicode(e) + '\n' + info
            fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)

    return xmlrpclib.dumps(fault)

def xmlrpc_convert_exception_stringcode(e):
    """ Legacy converter: historically Odoo has mis-generated XML-RPC fault by
    using a ``<string>`` as the ``<faultCode>`` even though it must be an
    ``<int>``.

    This function provides the old (incorrect) behavior where
    :func:`~.xml_convert_exception` implements the correct behavior of
    integral ``<faultCode>``
    """
    if isinstance(e, openerp.osv.orm.except_orm):
        fault = xmlrpclib.Fault('warning -- ' + e.name + '\n\n' + e.value, '')
    elif isinstance(e, openerp.exceptions.Warning):
        fault = xmlrpclib.Fault('warning -- Warning\n\n' + str(e), '')
    elif isinstance(e, openerp.exceptions.AccessError):
        fault = xmlrpclib.Fault('warning -- AccessError\n\n' + str(e), '')
    elif isinstance(e, openerp.exceptions.AccessDenied):
        fault = xmlrpclib.Fault('AccessDenied', str(e))
    elif isinstance(e, openerp.exceptions.DeferredException):
        info = e.traceback
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(openerp.tools.ustr(e.message), formatted_info)
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(openerp.tools.exception_to_unicode(e), formatted_info)

    return xmlrpclib.dumps(fault)

def wsgi_xmlrpc(environ, start_response):
    """ Two routes are available for XML-RPC

    /xmlrpc/<service> route returns faultCode as strings. This is a historic
    violation of the protocol kept for compatibility.

    /xmlrpc/2/<service> is a new route that returns faultCode as int and is
    therefore fully compliant.
    """
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/xmlrpc/'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        # Distinguish betweed the 2 faultCode modes
        string_faultcode = True
        if environ['PATH_INFO'].startswith('/xmlrpc/2/'):
            service = environ['PATH_INFO'][len('/xmlrpc/2/'):]
            string_faultcode = False
        else:
            service = environ['PATH_INFO'][len('/xmlrpc/'):]

        params, method = xmlrpclib.loads(data)
        return xmlrpc_return(start_response, service, method, params, string_faultcode)

# WSGI handlers registered through the register_wsgi_handler() function below.
module_handlers = []
# RPC endpoints registered through the register_rpc_endpoint() function below.
rpc_handlers = {}

def register_wsgi_handler(handler):
    """ Register a WSGI handler.

    Handlers are tried in the order they are added. We might provide a way to
    register a handler for specific routes later.
    """
    module_handlers.append(handler)

def register_rpc_endpoint(endpoint, handler):
    """ Register a handler for a given RPC enpoint.
    """
    rpc_handlers[endpoint] = handler

def application_unproxied(environ, start_response):
    """ WSGI entry point."""
    # cleanup db/uid trackers - they're set at HTTP dispatch in
    # web.session.OpenERPSession.send() and at RPC dispatch in
    # openerp.service.web_services.objects_proxy.dispatch().
    # /!\ The cleanup cannot be done at the end of this `application`
    # method because werkzeug still produces relevant logging afterwards 
    if hasattr(threading.current_thread(), 'uid'):
        del threading.current_thread().uid
    if hasattr(threading.current_thread(), 'dbname'):
        del threading.current_thread().dbname

    with openerp.api.Environment.manage():
        # Try all handlers until one returns some result (i.e. not None).
        wsgi_handlers = [wsgi_xmlrpc]
        wsgi_handlers += module_handlers
        for handler in wsgi_handlers:
            result = handler(environ, start_response)
            if result is None:
                continue
            return result

    # We never returned from the loop.
    response = 'No handler found.\n'
    start_response('404 Not Found', [('Content-Type', 'text/plain'), ('Content-Length', str(len(response)))])
    return [response]

def application(environ, start_response):
    if config['proxy_mode'] and 'HTTP_X_FORWARDED_HOST' in environ:
        return werkzeug.contrib.fixers.ProxyFix(application_unproxied)(environ, start_response)
    else:
        return application_unproxied(environ, start_response)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
