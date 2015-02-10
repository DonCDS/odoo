# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.addons.website_portal.controllers.main import website_account
from openerp.http import request
from openerp.tools import plaintext2html
from openerp.tools.translate import _


class website_contract(website_account):
    @http.route(['/account/contract/<int:account_id>'], type='http', auth="public", website=True)
    def contract(self, account_id):
        res_accounts = request.env['account.analytic.account']
        partner_comp = request.env.user.partner_id.commercial_partner_id
        account_cust = res_accounts.browse(account_id)
        account_templates = res_accounts.search([
            ('type', '=', 'template'),
            ('parent_id', '=', account_cust.template_id.parent_id.id)
            ])
        values = {}
        values['account_templates'] = account_templates
        values['account'] = account_cust
        values['terms'] = plaintext2html(account_cust.description)
        return request.website.render("website_contract.contract", values)

    @http.route(['/account'], type='http', auth="public", website=True)
    def account(self):
        response = super(website_contract, self).account()
        partner = request.env.user.partner_id
        values = {}

        res_accounts = request.env['account.analytic.account']
        cust_accounts = res_accounts.search([
            '|',
            ('partner_id.id', '=', partner.id),
            ('partner_id.id', '=', partner.commercial_partner_id.id)
            ])
        values['cust_accounts'] = cust_accounts

        response.qcontext.update(values)

        return response

    @http.route(['/account/contract/<int:account_id>/add/<int:option_id>'], type='http', auth="user", website=True)
    def add_option(self, account_id, option_id):
        res_accounts = request.env['account.analytic.account']
        account_cust = res_accounts.browse(account_id)
        account_cust.add_option(option_id)
        return request.redirect('/account/contract/'+str(account_id))

    @http.route(['/account/contract/<int:account_id>/remove/<int:inv_line_id>'], type='http', auth="user", website=True)
    def remove_option(self, account_id, inv_line_id):
        res_accounts = request.env['account.analytic.account']
        account_cust = res_accounts.browse(account_id)
        account_cust.remove_option(inv_line_id)
        return request.redirect('/account/contract/'+str(account_id))

    @http.route(['/account/contract/<int:account_id>/switch/<int:template_id>'], type='http', auth="user", website=True)
    def change_subscription(self, account_id, template_id):
        res_accounts = request.env['account.analytic.account']
        account_cust = res_accounts.browse(account_id)
        account_cust.change_subscription(template_id)
        return request.redirect('/account/contract/'+str(account_id))