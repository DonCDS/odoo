from openerp import _, api, fields, models
import urllib
import json


class ecb(models.Model):
    _inherit = "res.currency.rate.provider"

    @api.multi
    def _request_to_ecb(self):
        base_obj = self.env['res.currency.rate.provider'].search([('service_provider', '=', 'ecb')])
        if base_obj:
            return base_obj
