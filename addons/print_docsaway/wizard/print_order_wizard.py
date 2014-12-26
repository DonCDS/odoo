
from openerp import api, models


class print_order_wizard(models.TransientModel):

    _inherit = 'print.order.wizard'

    @api.onchange('provider_id')
    def _onchange_provider_id(self):
        super(print_order_wizard, self)._onchange_provider_id()
        if self.provider_id.provider == 'docsaway':
            self.currency_id = self.env['res.currency'].search([('name', '=', 'AUD')]).id
