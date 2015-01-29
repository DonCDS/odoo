# -*- coding: utf-8 -*-

from openerp import models, fields

class account_journal(models.Model):
    _inherit = "account.journal"

    sepa_payment_enabled = fields.Boolean(string="Enable SEPA payments")
