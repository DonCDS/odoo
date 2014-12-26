# -*- coding: utf-8 -*-
from openerp import api, models, fields


class res_partner(models.Model):

    _inherit = "res.partner"

    @api.depends('street', 'zip', 'country_id', 'state_id', 'city')
    def _compute_is_address_valid(self):
        for partner in self:
            partner.is_address_valid = bool(partner.street and partner.city and partner.zip and partner.country_id)

    is_address_valid = fields.Boolean(string='Is address valid', readonly=True, store=True, compute='_compute_is_address_valid')
