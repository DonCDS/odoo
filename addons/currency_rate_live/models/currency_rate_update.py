from openerp import models, fields, api, _
import json
import logging
from openerp import exceptions
_logger = logging.getLogger(__name__)


class Currency_rate_update(models.Model):
    _name = "res.currency.rate.provider"

    service_provider = fields.Selection([
            ('yahoo_finance', 'Yahoo Finance'),
            ('ecb', 'European Central Bank'),
            ('bancico', 'Bank Of Maxico'),
            ('bank_of_canada', 'Bank Of Canada'),
            ('pln', 'Polish National Bank'),
            ('swiss_custom', 'Swiss Custom Admin'),
            ('appspot', 'AppSpot'),
            ('quandl', 'Quandl'),
        ], string='Select service provider', required=True,
        default=lambda self: self._context.get('service_provider', 'yahoo_finance'))
    currency_ids = fields.Many2many('res.currency', size=3, string="Currencies to be update", required=True)
    company_id = fields.Many2one('res.company')
    base_currency_id = fields.Many2one('res.currency', string="Base currency", size=3, required=True, help="Input Base Currency name")
    request_token = fields.Char('Request token')
    # server_action_id = fields.Many2one('ir.action.server')

    @api.multi
    def update_rate(self):
        rate_obj = self.env['res.currency.rate']
        try:
            reuqest_method = '_parse_currency_data_' + self.service_provider
            method_to_call = getattr(self, reuqest_method)
            result = method_to_call()
            parse_data = json.dumps(result[0])
            json_data = json.loads(parse_data)
            for x in json_data:
                rate_obj.create(x)
        except TypeError:
            raise exceptions.Warning(_('You can use a service only one time per provider !'))
