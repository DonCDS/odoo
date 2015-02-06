# -*- coding: utf-8 -*-

from openerp import api, fields, models


class account_analytic_account(models.Model):
    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'

    @api.one
    @api.depends('recurring_invoice_line_ids')
    def _compute_base_price(self):
        base_price = 0
        for invoice_line in self.recurring_invoice_line_ids:
            if invoice_line.type == 'mandatory':
                base_price += invoice_line.price_subtotal
        self.base_price = base_price

    @api.one
    @api.depends('recurring_invoice_line_ids')
    def _compute_full_price(self):
        full_price = 0
        for invoice_line in self.recurring_invoice_line_ids:
                full_price += invoice_line.price_subtotal
        self.full_price = full_price

    def _search_upper(self, operator, value):
        return [('name', operator, value)]

    plan_description = fields.Html(
        string='Plan Description',
        help="Describe this contract in a few lines",
        )
    selectable_by_customer = fields.Boolean(
        string='User selectable',
        help="""Leave this unchecked if you don't want this contract
        template to be availableto the customer in the frontend
        (for a free trial, for example)""",
        default=True
        )
    base_price = fields.Float(compute=_compute_base_price)
    full_price = fields.Float(compute=_compute_full_price)


class account_analytic_invoice_line(models.Model):
    _name = "account.analytic.invoice.line"
    _inherit = "account.analytic.invoice.line"

    type = fields.Selection(
        selection=[('mandatory', 'Mandatory'), ('optional', 'Optional')],
        help="A mandatory invoice line cannot be removed from the contract",
        default="mandatory"
        )
    user_addable = fields.Boolean(
        string="Addable",
        help="If checked, the user is able to add this line to his contract himself",
        default=False
        )
    user_removable = fields.Boolean(
        string="Removable",
        help="If checked, the user is able to remove this line from his contract himself",
        default=False
        )
