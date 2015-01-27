# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.http import request
from openerp.tools import plaintext2html
from openerp.tools.translate import _



class website_contract(http.Controller):
    @http.route(['/account/contract/<int:account_id>'], type='http', auth="public", website=True)
    def contract(self,account_id):
        res_accounts = request.env['account.analytic.account']
        partner_comp = request.env.user.partner_id.commercial_partner_id;
        account_cust = res_accounts.browse(account_id)
        account_templates = res_accounts.search([('type','=','template'),('parent_id','=',account_cust.template_id.parent_id.id)])
        values = {}
        values['account_templates'] = account_templates
        values['account'] = account_cust
        values['terms'] = plaintext2html(account_cust.description)
        return request.website.render("website_contract.contract", values)
