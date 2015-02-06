from openerp import models, fields, api, _


class res_company(models.Model):
    _inherit = "res.company"

    currency_rate_live_interval = fields.Selection([
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ], string='Currency Update Frequency')
    display_list = fields.One2many('res.currency.rate.provider', 'company_id', string='Currency update services')

    @api.one
    def btn_update_currency(self):
        self.display_list.update_rate()
