# -*- coding: utf-8 -*-
from openerp import api, fields, models

class crm_partner_binding(models.TransientModel):
    """
    Handle the partner binding or generation in any CRM wizard that requires
    such feature, like the lead2opportunity wizard, or the
    phonecall2opportunity wizard.  Try to find a matching partner from the
    CRM model's information (name, email, phone number, etc) or create a new
    one on the fly.
    Use it like a mixin with the wizard of your choice.
    """
    _name = 'crm.partner.binding'
    _description = 'Handle partner binding or generation in CRM wizards.'

    action = fields.Selection([
            ('exist', 'Link to an existing customer'),
            ('create', 'Create a new customer'),
            ('nothing', 'Do not link to a customer')
        ], string='Related Customer', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    @api.model
    def _find_matching_partner(self):
        """
        Try to find a matching partner regarding the active model data, like
        the customer's name, email, phone number, etc.

        :return int partner_id if any, False otherwise
        """
        active_model = False
        partner_id = False
        partner_obj = self.env['res.partner']

        # The active model has to be a lead or a phonecall
        if (self._context.get('active_model') == 'crm.lead') and self._context.get('active_id'):
            active_model = self.env['crm.lead'].browse(self._context.get('active_id'))
        elif (self._context.get('active_model') == 'crm.phonecall') and self._context.get('active_id'):
            active_model = self.env['crm.phonecall'].browse(self._context.get('active_id'))

        # Find the best matching partner for the active model
        if (active_model):

            # A partner is set already
            if active_model.partner_id:
                partner_id = active_model.partner_id

            # Search through the existing partners based on the lead's email
            elif active_model.email_from:
                partner_id = partner_obj.search([('email', '=', active_model.email_from)], limit=1) or False
            # Search through the existing partners based on the lead's partner or contact name
            elif active_model.partner_name:
                partner_id = partner_obj.search([('name', 'ilike', '%'+active_model.partner_name+'%')], limit=1) or False
            elif active_model.contact_name:
                partner_id = partner_obj.search([('name', 'ilike', '%'+active_model.contact_name+'%')], limit=1) or False
        return partner_id

    @api.model
    def default_get(self, fields):
        res = super(crm_partner_binding, self).default_get(fields)
        partner = self._find_matching_partner()
        if 'action' in fields and not res.get('action'):
            res['action'] = partner and 'exist' or 'create'
        if 'partner_id' in fields:
            res['partner_id'] = partner and partner.id or False
        return res
