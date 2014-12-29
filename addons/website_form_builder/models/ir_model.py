# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models, fields, api

class website_config(models.Model):
    """ add a config boolean needed to Enable/Disable metadata writing on save """
    _name = 'res.config.settings'
    _inherit = 'res.config.settings'
    website_form_enable_metadata = fields.Boolean('Write metadata',help="Enable/Disable writting metadata on default_field")

class website_model(models.Model):
    """ Model configuration for form builder """
    _name = 'ir.model'
    _inherit = 'ir.model'

    website_form_access             = fields.Boolean('Public form access', string='Enable/Disable insert from public form')
    website_form_default_field_id   = fields.Many2one('ir.model.fields', 'Default Field', ondelete='set null', help="Specify the field wich will contain meta and custom datas")
    website_form_label              = fields.Char("Kind of action", help="Label to describe the action",translate=True)

    @api.one
    def get_authorized_fields(self):
        fields_name = []
        def fil(record):
            if record.name not in fields_name:
                fields_name.append(record.name)
                return True
            return False
        
        self.env['ir.model.fields'].search([('model_id', '=', self.id), ('website_form_blacklisted_register', '=', False)]).filtered(fil)
        return self

class website_model_fields(models.Model):
    """ fields configuration for form builder """
    _name = 'ir.model.fields'
    _inherit = 'ir.model.fields'

    website_form_blacklisted_register   = fields.Boolean('Blacklisted Field', string='Blacklist the Field')
    website_form_blacklisted            = fields.Boolean('Blacklisted Field', string='Blacklist the Field',compute='_get_blacklisted', inverse='_set_blacklisted')
    
    @api.one
    def _get_blacklisted(self):
        if self.website_form_blacklisted_register:
            return True
        return bool(self.search([('model_id', '=', self.model_id.id), ('name', '=', self.name), ('website_form_blacklisted_register', '=', True)], limit=1))

    @api.one
    def _set_blacklisted(self):
        self.search([('model_id', '=', self.model_id.id), ('name', '=', self.name)]).write({'website_form_blacklisted_register': True});

  
