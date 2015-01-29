# -*- coding: utf-8 -*-

from openerp import models, fields, api

class account_register_payment(models.Model):
    _inherit = "account.register.payment"

    pay_via_sepa = fields.Boolean(string="Pay via SEPA")
    sepa_payment_enabled = fields.Boolean(related='journal_id.sepa_payment_enabled')
    invoice_type = fields.Selection(related='invoice_id.type')

    @api.multi
    def _get_payment_account_move_line_vals(self, debit, credit, amount_currency):
        aml_dict = super(account_register_payment, self)._get_payment_account_move_line_vals(debit, credit, amount_currency)
        if self.invoice_id.type in ('in_invoice', 'in_refund') and self.pay_via_sepa:
            aml_dict.update({'payment_state': 'to_send'})
        return aml_dict
