# -*- coding: utf-8 -*-
import crm
from datetime import datetime
from openerp import api, fields, models, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError


class crm_phonecall(models.Model):

    """ Model for CRM phonecalls """
    _name = "crm.phonecall"
    _description = "Phonecall"
    _order = "id desc"
    _inherit = ['mail.thread']

    def _get_default_state(self):
        if self._context.get('default_state'):
            return self._context.get('default_state')
        return 'open'

    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    date_action_next = fields.Datetime(string='Next Action', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id',
                              select=True, help='Sales team to which Case belongs to.')
    user_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self._uid)
    partner_id = fields.Many2one('res.partner', string='Contact')
    company_id = fields.Many2one('res.company', string='Company')
    description = fields.Text()
    state = fields.Selection(
        [('open', 'Confirmed'),
         ('cancel', 'Cancelled'),
         ('pending', 'Pending'),
         ('done', 'Held')
         ], string='Status', readonly=True, track_visibility='onchange',
        help='The status is set to Confirmed, when a case is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the callis not applicable anymore, the status can be set to Cancelled.',
        default=lambda self: self._get_default_state())
    email_from = fields.Char(
        string='Email', size=128, help="These people will receive email.")
    date_open = fields.Datetime(string='Opened', readonly=True)
    # phonecall fields
    name = fields.Char(string='Call Summary', required=True)
    active = fields.Boolean(required=False, default=True)
    duration = fields.Float(help='Duration in minutes and seconds.')
    categ_id = fields.Many2one('crm.phonecall.category', string='Category')
    partner_phone = fields.Char(string='Phone')
    partner_mobile = fields.Char(string='Mobile')
    priority = fields.Selection(
        [('0', 'Low'), ('1', 'Normal'), ('2', 'High')], default='1')
    date_closed = fields.Datetime(string='Closed', readonly=True)
    date = fields.Datetime(string='Date', default=fields.datetime.now())
    opportunity_id = fields.Many2one('crm.lead', string='Lead/Opportunity')

    @api.multi
    def write(self, values):
        """ Override to add case management: open/close dates """
        if values.get('state'):
            if values.get('state') == 'done':
                values['date_closed'] = fields.datetime.now()
                self.compute_duration()
            elif values.get('state') == 'open':
                values['date_open'] = fields.datetime.now()
                values['duration'] = 0.0
        return super(crm_phonecall, self).write(values)

    @api.multi
    def compute_duration(self):
        for phonecall in self:
            if phonecall.duration <= 0:
                duration = datetime.now() - datetime.strptime(
                    phonecall.date, DEFAULT_SERVER_DATETIME_FORMAT)
                values = {'duration': duration.seconds / float(60)}
                self.write(values)
        return True

    @api.multi
    def schedule_another_phonecall(self, schedule_time, call_summary, user_id=False, team_id=False, categ_id=False, action='schedule'):
        """
        action :('schedule','Schedule a call'), ('log','Log a call')
        """
        phonecall_dict = {}
        if not categ_id:
            try:
                categ_id = self.env.ref('crm.categ_phone2').id
            except ValueError:
                pass
        for call in self:
            if not team_id:
                team_id = call.team_id and call.team_id.id or False
            if not user_id:
                user_id = call.user_id and call.user_id.id or False
            if not schedule_time:
                schedule_time = call.date
            vals = {
                    'name' : call_summary,
                    'user_id' : user_id or False,
                    'categ_id' : categ_id or False,
                    'description' : call.description or False,
                    'date' : schedule_time,
                    'team_id' : team_id or False,
                    'partner_id' : call.partner_id and call.partner_id.id or False,
                    'partner_phone' : call.partner_phone,
                    'partner_mobile' : call.partner_mobile,
                    'priority': call.priority,
                    'opportunity_id': call.opportunity_id and call.opportunity_id.id or False,
            }
            new_id = self.create(vals)
            if action == 'log':
                new_id.write({'state': 'done'})
            phonecall_dict[call.id] = new_id
        return phonecall_dict

    @api.one
    def _call_create_partner(self):
        partner_id = self.partner_id.create({
                    'name': self.name,
                    'user_id': self.user_id.id,
                    'comment': self.description,
                    'address': []
        })
        return partner_id.id

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        self.partner_phone = self.partner_id.phone
        self.partner_mobile = self.partner_id.mobile

    @api.onchange('opportunity_id')
    def on_change_opportunity(self):
        if self.opportunity_id:
            self.team_id = self.opportunity_id.team_id and self.opportunity_id.team_id.id or False
            self.partner_phone = self.opportunity_id.phone
            self.partner_mobile = self.opportunity_id.mobile
            self.partner_id = self.opportunity_id.partner_id and self.opportunity_id.partner_id.id or False

    @api.one
    def _call_set_partner(self, partner_id):
        write_res = self.write({'partner_id': partner_id})
        self._call_set_partner_send_note()
        return write_res

    @api.one
    def _call_create_partner_address(self, partner_id):
        return self.partner_id.create({
                'parent_id': partner_id,
                'name': self.name,
                'phone': self.partner_phone
        })

    @api.multi
    def handle_partner_assignation(self, action='create', partner_id=False):
        """
        Handle partner assignation during a lead conversion.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to specified partner_id

        :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
        :param int partner_id: partner to assign if any
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        # TODO this is a duplication of the handle_partner_assignation method of crm_lead
        partner_ids = {}
        # If a partner_id is given, force this partner for all elements
        force_partner_id = partner_id
        for call in self:
            # If the action is set to 'create' and no partner_id is set, create a new one
            if action == 'create':
                partner_id = force_partner_id or call._call_create_partner()
                call._call_create_partner_address(partner_id)
            call._call_set_partner(partner_id)
            partner_ids[call.id] = partner_id
        return partner_ids

    @api.multi
    def redirect_phonecall_view(self):
        # Select the view
        self.ensure_one()
        tree_view = self.env.ref('crm.crm_case_phone_tree_view').id
        form_view = self.env.ref('crm.crm_case_phone_form_view').id
        search_view = self.env.ref('crm.view_crm_case_phonecalls_filter').id
        value = {
            'name': _('Phone Call'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.phonecall',
            'res_id': self.id,
            'views': [(form_view, 'form'), (tree_view, 'tree'), (False, 'calendar')],
            'type': 'ir.actions.act_window',
            'search_view_id': search_view,
        }
        return value

    @api.multi
    def convert_opportunity(self, opportunity_summary=False, partner_id=False, planned_revenue=0.0, probability=0.0):
        partner = self.env['res.partner']
        opportunity_dict = {}
        default_contact = False
        for call in self:
            if not partner_id:
                partner_id = call.partner_id and call.partner_id.id or False
            if partner_id:
                address_id = call.partner_id.address_get()['default']
                if address_id:
                    default_contact = partner.browse(address_id)
            opportunity_id = call.opportunity_id.create({
                            'name': opportunity_summary or call.name,
                            'planned_revenue': planned_revenue,
                            'probability': probability,
                            'partner_id': partner_id or False,
                            'mobile': default_contact and default_contact.mobile,
                            'team_id': call.team_id and call.team_id.id or False,
                            'description': call.description or False,
                            'priority': call.priority,
                            'type': 'opportunity',
                            'phone': call.partner_phone or False,
                            'email_from': default_contact and default_contact.email
                            })
            vals = {
                'partner_id': partner_id,
                'opportunity_id': opportunity_id.id,
                'state': 'done'
            }
            call.write(vals)
            opportunity_dict[call.id] = opportunity_id
        return opportunity_dict

    @api.multi
    def action_make_meeting(self):
        """
        Open meeting's calendar view to schedule a meeting on current phonecall.
        :return dict: dictionary value for created meeting view
        """
        self.ensure_one()
        partner_ids = []
        if self.partner_id and self.partner_id.email:
            partner_ids.append(self.partner_id.id)
        res = self.env['ir.actions.act_window'].for_xml_id(
            'calendar', 'action_calendar_event')
        res['context'] = {
            'default_phonecall_id': self.id,
            'default_partner_ids': partner_ids,
            'default_user_id': self._uid,
            'default_email_from': self.email_from,
            'default_name': self.name,
            'default_opportunity_id': self.opportunity_id.id,
        }
        return res

    @api.multi
    def action_button_convert2opportunity(self):
        """
        Convert a phonecall into an opp and then redirect to the opp view.

        :return dict: containing view information
        """
        if len(self) != 1:
            raise UserError(_('It\'s only possible to convert one phonecall at a time.'))

        opportunity_dict = self.convert_opportunity()
        return opportunity_dict.values()[0].redirect_opportunity_view()

    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    @api.multi
    def _call_set_partner_send_note(self):
        return self.message_post(body=_("Partner has been <b>created</b>."))


class crm_phonecall_category(models.Model):
    _name = "crm.phonecall.category"
    _description = "Category of phonecall"
    name = fields.Char(required=True, translate=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')
