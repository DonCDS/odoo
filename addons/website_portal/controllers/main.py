# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.http import request
from openerp.tools.translate import _


class website_account(http.Controller):
    @http.route(['/account'], type='http', auth="public", website=True)
    def account(self):
        res_modules = request.env['ir.module.module']
        # checking if analytic and sale are installed
        inst_analytic = (res_modules.search([('name', '=', 'account_analytic_analysis')]).state == 'installed')
        inst_sale = (res_modules.search([('name', '=', 'sale')]).state == 'installed')
        partner = request.env.user.partner_id
        values = {}
        values['inst_analytic'] = inst_analytic
        values['inst_sale'] = inst_sale

        if inst_analytic:
            res_accounts = request.env['account.analytic.account']
            cust_accounts = res_accounts.search([
                '|',
                ('partner_id.id', '=', partner.id),
                ('partner_id.id', '=', partner.commercial_partner_id.id)
                ])
            values['cust_accounts'] = cust_accounts

        if inst_sale:
            res_sale_order = request.env['sale.order']
            res_invoices = request.env['account.invoice']
            cust_quotations = res_sale_order.search([
                '&',
                '|',
                ('partner_id.id', '=', partner.id),
                ('partner_id.id', '=', partner.commercial_partner_id.id),
                ('state', '=', 'sent')
                ])
            cust_orders = res_sale_order.search([
                '&',
                '|',
                ('partner_id.id', '=', partner.id),
                ('partner_id.id', '=', partner.commercial_partner_id.id),
                ('state', 'in', ['progress', 'manual', 'shipping_except', 'invoice_except', 'done'])
                ])
            cust_invoices = res_invoices.search([
                '&',
                '|',
                ('partner_id.id', '=', partner.id),
                ('partner_id.id', '=', partner.commercial_partner_id.id),
                ('state', 'in', ['open', 'paid', 'cancelled'])
                ])

            values['cust_quotations'] = cust_quotations
            values['cust_orders'] = cust_orders
            values['cust_invoices'] = cust_invoices

        # get customer sales rep
        if partner.user_id:
            sales_rep = partner.user_id
        elif partner.commercial_partner_id and partner.commercial_partner_id.user_id:
            sales_rep = partner.commercial_partner_id.user_id
        else:
            sales_rep = False
        values['sales_rep'] = sales_rep
        values['company'] = request.website.company_id

        return request.website.render("website_portal.account", values)

    @http.route([
                '/account/orders',
                '/account/orders/page/<int:page>',
                '/account/orders/<int:order>'
                ], type='http', auth="user", website=True)
    def orders_followup(self, page=1, order=None, by=5, **post):
        partner = request.env['res.users'].browse(request.uid).partner_id
        domain = [
            ('partner_id', '=', partner.id),
            ('state', 'not in', ['draft', 'cancel'])
            ]
        if order:
            domain.append(('id', '=', order))
        orders = request.env['sale.order'].sudo().search(domain)

        nbr_pages = max((len(orders) / by) + (1 if len(orders) % by > 0 else 0), 1)
        page = min(page, nbr_pages)
        pager = request.website.pager(
            url='/account/orders', total=nbr_pages, page=page, step=1,
            scope=by, url_args=post
        )
        orders = orders[by*(page-1):by*(page-1)+by]

        order_invoice_lines = {}
        for o in orders:
            invoiced_lines = request.env['account.invoice.line'].sudo().search([('invoice_id', 'in', o.invoice_ids.ids)])
            order_invoice_lines[o.id] = {il.product_id.id: il.invoice_id for il in invoiced_lines}

        return request.website.render("website_portal.orders_followup", {
            'orders': orders,
            'order_invoice_lines': order_invoice_lines,
            'pager': pager,
        })
