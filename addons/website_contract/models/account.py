# -*- coding: utf-8 -*-

from openerp import fields, models

class account_analytic_account(models.Model):
    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'

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
