# -*- coding: utf-8 -*-
from openerp import api, fields, models


class print_order_sendnow_wizard(models.TransientModel):

    _name = 'print.order.sendnow.wizard'
    _rec_name = 'create_date'

    # --------------------------------------------------
    # MODEL FIELDS
    # --------------------------------------------------
    print_order_sendnow_line_wizard_ids = fields.One2many('print.order.sendnow.line.wizard', 'print_order_sendnow_wizard_id', string='Lines')

    # --------------------------------------------------
    # METHODS
    # --------------------------------------------------
    @api.model
    def default_get(self, fields):
        """ create the lines on the wizard """
        res = super(print_order_sendnow_wizard, self).default_get(fields)
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            # create order lines
            lines = []
            for rec in self.env['print.order'].browse(active_ids):
                if rec.state != 'sent':
                    lines.append((0, 0, {
                        'res_model': rec.res_model,
                        'ink' : rec.ink,
                        'partner_id' : rec.partner_id.id,
                        'provider_id' : rec.provider_id.id,
                        'state' : rec.state,
                        'order_id' : rec.id
                    }))
            res['print_order_sendnow_line_wizard_ids'] = lines
        return res

    @api.multi
    def action_apply(self):
        Print_order = self.env['print.order']
        for wizard in self:
            order_ids = [line.order_id.id for line in wizard.print_order_sendnow_line_wizard_ids]
            Print_order.process_order_queue(order_ids)
        return {'type': 'ir.actions.act_window_close'}



class print_order_sendnow_line_wizard(models.TransientModel):

    _name = 'print.order.sendnow.line.wizard'

    # --------------------------------------------------
    # MODEL FIELDS
    # --------------------------------------------------
    print_order_sendnow_wizard_id = fields.Many2one('print.order.sendnow.wizard', 'Send Now Wizard')

    order_id = fields.Many2one('print.order', 'Print Order')
    res_model = fields.Char('Model Name')
    ink = fields.Selection([('BW', 'Black & White'), ('CL', 'Colour')], "Ink", default='BW')
    partner_id = fields.Many2one('res.partner', 'Recipient partner')
    provider_id = fields.Many2one('print.provider', 'Provider')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('ready_to_send', 'Ready'),
            ('error', 'Failed'),
            ('sent', 'Sent'),
        ], string='Status', default='draft', readonly=True, required=True)
