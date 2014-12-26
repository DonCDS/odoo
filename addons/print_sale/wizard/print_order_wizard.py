# -*- coding: utf-8 -*-
from openerp import api, models

class print_order_line_wizard(models.TransientModel):

    _inherit = 'print.order.line.wizard'

    @api.model
    def _default_selection_state(self):
        selection = super(print_order_line_wizard, self)._default_selection_state()
        selection.append(('bad_sale_order_state', 'Wrong Sale Order State'))
        return selection

    @api.one
    def _compute_state(self):
        super(print_order_line_wizard, self)._compute_state()
        state = self.state
        if self.res_model == 'sale.order':
            if not self.env['sale.order'].browse(self.res_id).state in ['draft', 'sent', 'progress', 'manual']:
                state = 'bad_sale_order_state'
        self.state = state
