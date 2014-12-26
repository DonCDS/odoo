# -*- coding: utf-8 -*-
from openerp import api, models
from openerp.tools.translate import _


class account_invoice(models.Model):
    """ Printable account_invoice.
    """

    _name = 'account.invoice'
    _inherit = ['account.invoice', 'print.mixin']

    def print_validate_sending(self):
        super(account_invoice, self).print_validate_sending()
        PrintOrder = self.env['print.order']
        for record in self:
            order = PrintOrder.search([('res_model', '=', 'account.invoice'), ('res_id', '=', record.id)], limit=1, order='send_date desc')
            if order:
                # put confirmation message in the chatter
                message = _("This invoice was sent by post with the provider <i>%s</i> at the following address. <br/><br/> \
                             %s <br/> %s <br/> %s %s<br/>%s") % (order.provider_id.name, order.partner_name, order.partner_street, order.partner_city, order.partner_zip, order.partner_country_id.name)
                record.sudo(user=order.user_id.id).message_post(body=message)
        # save sending data
        self.write({
            'sent' : True
        })

