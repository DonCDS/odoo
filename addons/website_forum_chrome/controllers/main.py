
import base64
import simplejson
import werkzeug

import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers.main import content_disposition

class WebsiteForum(openerp.addons.website_forum.controllers.main.WebsiteForum):

    def _is_allow_chrome_extension(self, forum):
        print "\n\nallow_chrome_extension is ::: ", forum.allow_chrome_extension 
        return forum.allow_chrome_extension

    def _prepare_forum_values(self, forum=None, **kwargs):
        res = super(WebsiteForum, self)._prepare_forum_values(forum=forum, **kwargs)
        res.update({'is_allow_chrome_extension': self._is_allow_chrome_extension(forum)})
        return res

class WebsiteForumChrome(http.Controller):

    @http.route(['''/forum/<model("forum.forum"):forum>/download_plugin'''], type='http', auth="public", website=True)
    def download_plugin(self, forum, **post):
        print "\n\nInside download_plugin ::: ", forum, "and posts are ::: ", post
        #TODO: Create generate configuration, create temp directory, put all the files in temp directory,
        #put config file generated in static -> src -> js -> config.json
        #Create zip file and return with proper content-type
        filename = "forum_link_extension.zip"
        headers = [
                ('Content-Type', 'application/octet-stream; charset=binary'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        extension_stream = forum.generate_extension()
        response = werkzeug.wrappers.Response(extension_stream, headers=headers, direct_passthrough=True)
        return response