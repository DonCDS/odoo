# -*- coding: utf-8 -*-
from openerp import api, models, _
from openerp.exceptions import UserError


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        line_ids = super(sale_order, self)._cart_find_product_line(product_id, line_id)
        if line_id:
            return line_ids
        domain = [('id', 'in', line_ids)]
        for so in self:
            if self.env.context.get("event_ticket_id"):
                domain += [('event_ticket_id', '=', self.env.context.get("event_ticket_id"))]
            return self.env['sale.order.line'].sudo().search(domain).ids

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0, line_id=None):
        values = super(sale_order, self)._website_product_id_change(order_id, product_id, qty=qty, line_id=line_id)
        event_ticket_id = None
        if self.env.context.get("event_ticket_id"):
            event_ticket_id = self.env.context.get("event_ticket_id")
        elif line_id:
            line = self.env['sale.order.line'].sudo().browse(line_id)
            if line.event_ticket_id:
                event_ticket_id = line.event_ticket_id.id
        else:
            product = self.env['product.product'].browse(product_id)
            if product.event_ticket_ids:
                event_ticket_id = product.event_ticket_ids[0].id

        if event_ticket_id:
            ticket = self.env['event.event.ticket'].browse(event_ticket_id)
            if product_id != ticket.product_id.id:
                raise UserError(_("The ticket doesn't match with this product."))

            values['product_id'] = ticket.product_id.id
            values['event_id'] = ticket.event_id.id
            values['event_ticket_id'] = ticket.id
            values['price_unit'] = ticket.price
            values['name'] = "%s: %s" % (ticket.event_id.name, ticket.name)
        return values

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        OrderLine = self.env['sale.order.line']
        Attendee = self.env['event.registration']
        Ticket = self.env['event.event.ticket']

        if line_id:
            line = OrderLine.browse(line_id)
            ticket = line.event_ticket_id
            old_qty = int(line.product_uom_qty)
        else:
            line, ticket = None, Ticket.search([('product_id', '=', product_id)], limit=1) or None
            old_qty = 0
        new_qty = set_qty if set_qty else (add_qty or 0 + old_qty)

        # case: buying tickets for a sold out ticket
        values = {}
        if ticket and ticket.seats_available <= 0:
            values['warning'] = _('Sorry, The %(ticket)s tickets for the %(event)s event are sold out.') % {
                'ticket': ticket.name,
                'event': ticket.event_id.name}
            new_qty, set_qty, add_qty = 0, 0, 0
        # case: buying tickets, too much attendees
        elif ticket and new_qty > ticket.seats_available:
            values['warning'] = _('Sorry, only %(remaining_seats)d seats are still available for the %(ticket)s ticket for the %(event)s event.') % {
                'remaining_seats': ticket.seats_available,
                'ticket': ticket.name,
                'event': ticket.event_id.name}
            new_qty, set_qty, add_qty = ticket.seats_available, ticket.seats_available, 0

        values.update(super(sale_order, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs))

        # removing attendees
        if ticket and new_qty < old_qty:
            attendees = Attendee.search(
                [
                    ('state', '!=', 'cancel'),
                    ('sale_order_id', '=', self.ids[0])
                    ('event_ticket_id', '=', ticket.id)
                ], offset=new_qty, limit=(old_qty-new_qty),
                order='create_date asc')
            Attendee.button_reg_cancel(attendees)
        # adding attendees
        elif ticket and new_qty > old_qty:
            line = OrderLine.browse(values['line_id'])
            line._update_registrations(confirm=False, registration_data=kwargs.get('registration_data', []))
        return values
