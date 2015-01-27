# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.http import request
from openerp.tools.translate import _



class website_contract(http.Controller):
    @http.route(['/account/contract'], type='http', auth="public", website=True)
    def contract(self):
        # import pudb
        # pudb.set_trace()
        an_accounts = request.env['account.analytic.account']
        account_templates = an_accounts.search([('type','=','template')])
        partner_comp = request.env.user.partner_id.commercial_partner_id;
        account_cust = an_accounts.search([('partner_id.id','=',partner_comp.id)])
        values = {}
        values['account_templates'] = account_templates
        values['account'] = account_cust[0]
        return request.website.render("website_contract.contract", values)
