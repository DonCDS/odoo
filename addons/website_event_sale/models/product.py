# -*- coding: utf-8 -*-
from openerp import models, fields

# defined for access rules
class product(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')
