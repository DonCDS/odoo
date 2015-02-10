# -*- encoding: utf-8 -*-

from openerp import fields, models


class certification_type(models.Model):
    _name = 'certification.type'
    _order = 'name ASC'

    name = fields.Char(string='Certification Type', required=True)


class certification_certification(models.Model):
    _name = 'certification.certification'
    _order =  'certification_date DESC'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    type_id = fields.Many2one('certification.type', string='Certification', required=True)
    certification_date = fields.Date(string='Certification Date', required=True)
    certification_score = fields.Char(string='Certification Score', required=True)
    certification_hidden_score = fields.Boolean(string='Hide score on website?')
