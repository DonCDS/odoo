# -*- coding: utf-8 -*-
from openerp import api, models
from openerp.tools.translate import _


class sale_order(models.Model):
    """ Printable sale_order """

    _name = 'sale.order'
    _inherit = ['sale.order', 'print.mixin']

    def print_validate_sending(self):
        PrintOrder = self.env['print.order']
        for record in self:
            order = PrintOrder.search([('res_model', '=', 'sale.order'), ('res_id', '=', record.id)], limit=1, order='send_date desc')
            # put confirmation message in the chatter
            message = _("This sale order was sent by post with the provider <i>%s</i> at the following address. <br/><br/> \
                         %s <br/> %s <br/> %s %s<br/>%s") % (order.provider_id.name, order.partner_name, order.partner_street, order.partner_city, order.partner_zip, order.partner_country_id.name)
            record.sudo(user=order.user_id.id).message_post(body=message)

        super(sale_order, self).print_validate_sending()

        # make the transition to the sent state
        self.signal_workflow('quotation_sent')

