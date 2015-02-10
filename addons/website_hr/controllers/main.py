# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request

class website_hr(http.Controller):

    @http.route(['/page/website.aboutus', '/page/aboutus'], type='http', auth="public", website=True)
    def aboutus(self, **post):
        domain = [] if request.env['res.users'].has_group('base.group_website_publisher') else [('website_published', '=', True)]
        values = {
            'employee_ids': request.env['hr.employee'].search(domain),
        }
        return request.website.render("website.aboutus", values)
