# -*- coding: utf-8 -*-
from openerp import api, fields, models

class crm_phonecall2meeting(models.TransientModel):
    """ Phonecall to Meeting """

    _name = 'crm.phonecall2meeting'
    _description = 'Phonecall To Meeting'

    @api.multi
    def action_cancel(self):
        """
        Closes Phonecall to Meeting form
        @param self: The object pointer

        """
        return {'type':'ir.actions.act_window_close'}

    @api.multi
    def action_make_meeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        res = {}
        phonecall_id = self._context and self._context.get('active_id', False) or False
        if phonecall_id:
            phonecall = self.env['crm.phonecall'].browse(phonecall_id)
            res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
            res['context'] = {
                'default_phonecall_id': phonecall.id,
                'default_partner_id': phonecall.partner_id and phonecall.partner_id.id or False,
                'default_user_id': self._uid,
                'default_email_from': phonecall.email_from,
                'default_state': 'open',
                'default_name': phonecall.name,
            }
        return res
