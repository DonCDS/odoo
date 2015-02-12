# -*- coding: utf-8 -*-

from openerp import api, fields, models


class res_partner(models.Model):
    _inherit = 'res.partner'

    tag_ids = fields.Many2many('res.partner.tag',
        column1='partner_id', column2='tag_id', string='Tags')


class res_partner_tags(models.Model):
    _description = 'Partner Tags - These tags can be used on website to find customers by sector, or ... '
    _name = 'res.partner.tag'
    _inherit = 'website.published.mixin'

    @api.model
    def get_selection_class(self):
        classname = ['default', 'primary', 'success', 'warning', 'danger']
        return [(x, str.title(x)) for x in classname]

    name = fields.Char(string='Category Name', required=True, translate=True)
    partner_ids = fields.Many2many('res.partner',
        'res_partner_res_partner_tag_rel', 'tag_id', 'partner_id',
        string='Partners')
    classname = fields.Selection('get_selection_class', string='Class',
        help="Bootstrap class to customize the color of the tag", required=True,
        default='default')
    active = fields.Boolean(string='Active', default=True)
    website_published = fields.Boolean(default=True)
