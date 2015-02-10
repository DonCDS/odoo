# -*- coding: utf-8 -*-

from openerp import api, fields, models

class account_analytic_account(models.Model):
    _inherit = "account.analytic.account"
    _name = "account.analytic.account"

    recurring_price = fields.Float(string="Recurring Price", compute="_compute_recurring_price")

    @api.one
    @api.depends('recurring_invoice_line_ids')
    def _compute_recurring_price(self):
        recurring_price = 0
        for invoice_line in self.recurring_invoice_line_ids:
                recurring_price += invoice_line.price_subtotal
        self.recurring_price = recurring_price


class account_analytic_invoice_line_option(models.Model):
    _inherit = "account.analytic.invoice.line"
    _name = "account.analytic.invoice.line.option"
    portal_access = fields.Selection(
        string='Portal Access',
        selection=[
            ('none', 'Restricted'),
            ('upgrade', 'Upgrade only'),
            ('both', 'Upgrade and Downgrade')],
        required=True,
        help="""Restricted: The user must ask a Sales Rep to add or remove this option
Upgrade Only: The user can add the option himself but must ask to remove it
Upgrade and Downgrade: The user can add or remove this option himself""")


class account_annalytic_account(models.Model):
    _inherit = "account.analytic.account"
    _name = "account.analytic.account"

    def add_option(self, option_id):
        option = self.env['account.analytic.invoice.line.option'].browse(option_id)
        if option not in self.template_id.option_invoice_line_ids:
            return False
        values = {
            'product_id': option.product_id.id,
            'analytic_account_id': self.id,
            'name': option.name,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
            'price_unit': option.price_unit,
            }
        self.write({'recurring_invoice_line_ids': [(0, 0, values)]})

    def remove_option(self, inv_line_id):
        inv_line = self.env['account.analytic.invoice.line'].browse(inv_line_id)
        if inv_line not in self.recurring_invoice_line_ids:
            return False
        self.write({'recurring_invoice_line_ids': [(2, inv_line_id)]})

    def change_subscription(self, template_id):
        """Change the template of a contract with contract_type 'subscription',
        remove the recurring_invoice_line_ids linked to that template and add the
        recurring_invoice_line_ids linked to the new template. Other invoicing lines
        are left unchanged"""
        values = {}
        rec_lines_to_remove = []
        rec_lines_to_add = []
        new_template = self.browse(template_id)
        for line in self.recurring_invoice_line_ids:
            if line.product_id in [tmp_line.product_id for tmp_line in self.template_id.recurring_invoice_line_ids]:
                rec_lines_to_remove.append((2, line.id))
        rec_lines_to_add = [(0, 0, {
            'product_id': tmp_line.product_id.id,
            'uom_id': tmp_line.uom_id.id,
            'name': tmp_line.name,
            'quantity': tmp_line.quantity,
            'price_unit': tmp_line.price_unit,
            'analytic_account_id': self.id,
            }) for tmp_line in new_template.recurring_invoice_line_ids]
        values['recurring_invoice_line_ids'] = rec_lines_to_add + rec_lines_to_remove
        self.write(values)
        self.template_id = new_template

