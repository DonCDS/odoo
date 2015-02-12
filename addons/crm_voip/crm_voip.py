# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _
import openerp
import time
from datetime import datetime
from datetime import timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------


class crm_phonecall(models.Model):
    _inherit = "crm.phonecall"

    _order = "sequence, id"

    in_queue = fields.Boolean('In Call Queue', default=True)
    sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of Phonecalls.")
    start_time = fields.Integer("Start time")
    state = fields.Selection([
        ('no_answer', 'Not Held'),
        ('cancel', 'Cancelled'),
        ('to_do', 'To Do'),
        ('done', 'Held')
        ], string='Status', readonly=True, track_visibility='onchange',
        help='The status is set to To Do, when a case is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the call is not applicable anymore, the status can be set to Cancelled.')
    opportunity_id = fields.Many2one('crm.lead', 'Lead/Opportunity', ondelete='cascade', track_visibility='onchange')

    _defaults = {
        'date': fields.Datetime.now(),
        'priority': '1',
        'state':  'to_do',
        'user_id': lambda self, cr, uid, ctx: uid,
        'active': 1
    }

    def write(self, cr, uid, ids, values, context=None):
        return super(crm_phonecall, self).write(cr, uid, ids, values, context=context)

    def schedule_another_phonecall(self, cr, uid, ids, schedule_time, call_summary,
                                   user_id=False, section_id=False, categ_id=False, context=None):
        model_data = self.pool.get('ir.model.data')
        phonecall_dict = {}
        if not categ_id:
            try:
                res_id = model_data._get_id(cr, uid, 'crm', 'categ_phone2')
                categ_id = model_data.browse(cr, uid, res_id, context=context).res_id
            except ValueError:
                pass
        for call in self.browse(cr, uid, ids, context=context):
            if(call.state != "done"):
                call.state = "cancel"
                call.in_queue = False
            if not section_id:
                section_id = call.section_id and call.section_id.id or False
            if not user_id:
                user_id = call.user_id and call.user_id.id or False
            if not schedule_time:
                schedule_time = call.date
            vals = {
                'name': call_summary,
                'user_id': user_id or False,
                'categ_id': categ_id or False,
                'description': False,
                'date': schedule_time,
                'section_id': section_id or False,
                'partner_id': call.partner_id and call.partner_id.id or False,
                'partner_phone': call.partner_phone,
                'partner_mobile': call.partner_mobile,
                'priority': call.priority,
                'opportunity_id': call.opportunity_id and call.opportunity_id.id or False,
            }
            new_id = self.create(cr, uid, vals, context=context)
            phonecall_dict[call.id] = new_id
        return phonecall_dict

    def convert_opportunity(self, cr, uid, ids, opportunity_summary=False, partner_id=False, planned_revenue=0.0, probability=0.0, context=None):
        partner = self.pool.get('res.partner')
        opportunity = self.pool.get('crm.lead')
        opportunity_dict = {}
        default_contact = False
        for call in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = call.partner_id and call.partner_id.id or False
            if partner_id:
                address_id = partner.address_get(cr, uid, [partner_id])['default']
                if address_id:
                    default_contact = partner.browse(cr, uid, address_id, context=context)
            opportunity_id = opportunity.create(cr, uid, {
                'name': opportunity_summary or call.name,
                'planned_revenue': planned_revenue,
                'probability': probability,
                'partner_id': partner_id or False,
                'mobile': default_contact and default_contact.mobile,
                'section_id': call.section_id and call.section_id.id or False,
                'description': call.description or False,
                'priority': call.priority,
                'type': 'opportunity',
                'phone': call.partner_phone or False,
                'email_from': default_contact and default_contact.email,
            })
            vals = {
                'partner_id': partner_id,
                'opportunity_id': opportunity_id,
            }
            self.write(cr, uid, [call.id], vals, context=context)
            opportunity_dict[call.id] = opportunity_id
        return opportunity_dict

    @api.multi
    def init_call(self):
        self.start_time = int(time.time())

    @api.multi
    def hangup_call(self):
        stop_time = int(time.time())
        duration = float(stop_time - self.start_time)
        self.duration = float(duration/60.0)
        self.state = "done"
        return {"duration": self.duration}

    @api.multi
    def rejected_call(self):
        self.state = "no_answer"

    @api.multi
    def remove_from_queue(self):
        self.in_queue = False
        if(self.state == "to_do"):
            self.state = "cancel"
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }

    @api.one
    def get_info(self):
        return {"id": self.id,
                "description": self.description,
                "name": self.name,
                "state": self.state,
                "date": self.date,
                "duration": self.duration,
                "partner_id": self.partner_id.id,
                "partner_name": self.partner_id.name,
                "partner_image_small": self.partner_id.image_small,
                "partner_email": self.partner_id.email,
                "partner_title": self.partner_id.title.name,
                "partner_phone": self.partner_phone or self.partner_mobile or self.opportunity_id.phone or self.opportunity_id.partner_id.phone or self.opportunity_id.partner_id.mobile or False,
                "opportunity_name": self.opportunity_id.name,
                "opportunity_id": self.opportunity_id.id,
                "opportunity_priority": self.opportunity_id.priority,
                "opportunity_planned_revenue": self.opportunity_id.planned_revenue,
                "opportunity_title_action": self.opportunity_id.title_action,
                "opportunity_date_action": self.opportunity_id.date_action,
                "opportunity_company_currency": self.opportunity_id.company_currency.id,
                "opportunity_probability": self.opportunity_id.probability,
                "max_priority": self.opportunity_id._fields['priority'].selection[-1][0]}

    @api.model
    def get_list(self):
        return {"phonecalls": self.search([('in_queue','=',True),('user_id','=',self.env.user[0].id)], order='sequence,id').get_info()}


class crm_lead(models.Model):
    _inherit = "crm.lead"
    in_call_center_queue = fields.Boolean("Is in the Call Queue", compute='compute_is_call_center')

    @api.one
    def compute_is_call_center(self):
        phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('in_queue','=',True),('state','!=','done'),('user_id','=',self.env.user[0].id)])
        if phonecall:
            self.in_call_center_queue = True
        else:
            self.in_call_center_queue = False

    @api.multi
    def create_call_in_queue(self):
        for opp in self:
            phonecall = self.env['crm.phonecall'].create({
                'name': opp.name,
                'duration': 0,
                'user_id': self.env.user[0].id,
                'opportunity_id': opp.id,
                'partner_id': opp.partner_id.id,
                'state': 'to_do',
                'partner_phone': opp.phone or opp.partner_id.phone,
                'partner_mobile': opp.partner_id.mobile,
                'in_queue': True,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }

    @api.multi
    def create_custom_call_center_call(self):
        import pudb
        pudb.set_trace()
        phonecall = self.env['crm.phonecall'].create({
            'name': self.name,
            'duration': 0,
            'user_id': self.env.user[0].id,
            'opportunity_id': self.id,
            'partner_id': self.partner_id.id,
            'state': 'to_do',
            'partner_phone': self.phone or self.partner_id.phone,
            'in_queue': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'src_model': "crm.phonecall",
            'res_model': "crm.custom.phonecall.wizard",
            'multi': "True",
            'target': 'new',
            'context': {'phonecall_id': phonecall.id,
                        'default_name': phonecall.name,
                        'default_partner_id': phonecall.partner_id.id,
                        'default_user_id': self.env.user[0].id,
                        },
            'views': [[False, 'form']],
        }

    @api.multi
    def delete_call_center_call(self):
        phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('in_queue','=',True),('user_id','=',self.env.user[0].id)])
        phonecall.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }

    @api.multi
    def log_new_phonecall(self):
        phonecall = self.env['crm.phonecall'].create({
            'name': self.name,
            'user_id': self.env.user[0].id,
            'opportunity_id': self.id,
            'partner_id': self.partner_id.id,
            'state': 'done',
            'partner_phone': self.phone or self.partner_id.phone,
            'partner_mobile': self.partner_id.mobile,
            'in_queue': False,
        })
        return {
            'name': 'Log a call',
            'type': 'ir.actions.act_window',
            'key2': 'client_action_multi',
            'src_model': "crm.phonecall",
            'res_model': "crm.phonecall.log.wizard",
            'multi': "True",
            'target': 'new',
            'context': {'phonecall_id': phonecall.id,
                        'default_opportunity_id': phonecall.opportunity_id.id,
                        'default_name': phonecall.name,
                        'default_duration': phonecall.duration,
                        'default_description': phonecall.description,
                        'default_opportunity_name': phonecall.opportunity_id.name,
                        'default_opportunity_planned_revenue': phonecall.opportunity_id.planned_revenue,
                        'default_opportunity_title_action': phonecall.opportunity_id.title_action,
                        'default_opportunity_date_action': phonecall.opportunity_id.date_action,
                        'default_opportunity_probability': phonecall.opportunity_id.probability,
                        'default_partner_id': phonecall.partner_id.id,
                        'default_partner_name': phonecall.partner_id.name,
                        'default_partner_email': phonecall.partner_id.email,
                        'default_partner_phone': phonecall.opportunity_id.phone or phonecall.partner_id.phone,
                        'default_partner_image_small': phonecall.partner_id.image_small,},
                        'default_show_duration': self._context.get('default_show_duration'),
            'views': [[False, 'form']],
            'flags': {
                'headless': True,
            },
        }


class res_partner(models.Model):
    _inherit = "res.partner"

    @api.one
    def create_call_in_queue(self, number):
        phonecall = self.env['crm.phonecall'].create({
            'name': 'Call for ' + self.name,
            'duration': 0,
            'user_id': self.env.user[0].id,
            'partner_id': self.id,
            'state': 'to_do',
            'partner_phone': number,
            'in_queue': True,
            'sequence': 1,
        })
        return phonecall.id


class crm_phonecall_log_wizard(models.TransientModel):
    _name = 'crm.phonecall.log.wizard'

    description = fields.Text('Description')
    name = fields.Char(readonly=True)
    opportunity_id = fields.Integer(readonly=True)
    opportunity_name = fields.Char(readonly=True)
    opportunity_planned_revenue = fields.Char(readonly=True)
    opportunity_title_action = fields.Char('Next Action')
    opportunity_date_action = fields.Date('Next Action Date')
    opportunity_probability = fields.Float(readonly=True)
    partner_id = fields.Integer(readonly=True)
    partner_name = fields.Char(readonly=True)
    partner_email = fields.Char(readonly=True)
    partner_phone = fields.Char(readonly=True)
    partner_image_small = fields.Char(readonly=True)
    duration = fields.Char('Duration', readonly=True)
    reschedule_option = fields.Selection([('no_reschedule', "Don't Reschedule"), ('1d', 'Tomorrow'), ('7d', 'In 1 Week'), ('15d', 'In 15 Day'), ('2m', 'In 2 Months'), ('custom', 'Specific Date')],
                                         'Schedule A New Call', required=True, default="no_reschedule")
    reschedule_date = fields.Datetime('Specific Date', default=lambda *a: datetime.now() + timedelta(hours=2))
    new_title_action = fields.Char('Next Action')
    new_date_action = fields.Date()
    show_duration = fields.Boolean()
    custom_duration = fields.Float(default=0)
    in_automatic_mode = fields.Boolean()

    def schedule_again(self):
        new_phonecall = self.env['crm.phonecall'].create({
            'name': self.name,
            'duration': 0,
            'user_id': self.env.user[0].id,
            'opportunity_id': self.opportunity_id,
            'partner_id': self.partner_id,
            'state': 'to_do',
            'partner_phone': self.partner_phone,
            'in_queue': True,
        })
        if self.reschedule_option == "7d":
            new_phonecall.date = datetime.now() + timedelta(weeks=1)
        elif self.reschedule_option == "1d":
            new_phonecall.date = datetime.now() + timedelta(days=1)
        elif self.reschedule_option == "15d":
            new_phonecall.date = datetime.now() + timedelta(days=15)
        elif self.reschedule_option == "2m":
            new_phonecall.date = datetime.now() + timedelta(weeks=8)
        elif self.reschedule_option == "custom":
            new_phonecall.date = self.reschedule_date

    @api.multi
    def modify_phonecall(self, phonecall):
        phonecall.description = self.description
        if(self.opportunity_id):
            opportunity = self.env['crm.lead'].browse(self.opportunity_id)
            if self.new_title_action and self.new_date_action:
                opportunity.title_action = self.new_title_action
                opportunity.date_action = self.new_date_action
            else:
                opportunity.title_action = self.opportunity_title_action
                opportunity.date_action = self.opportunity_date_action
            if (self.show_duration):
                mins = int(self.custom_duration)
                sec = (self.custom_duration - mins)*0.6
                sec = '%.2f' % sec
                time = str(mins) + ":" + sec[-2:]
                message = "Call " + time + " min(s)"
                phonecall.duration = self.custom_duration
            else:
                message = "Call " + self.duration + " min(s)"
            if(phonecall.description):
                message += " about " + phonecall.description
            opportunity.message_post(message)
        if self.reschedule_option != "no_reschedule":
            self.schedule_again()

    @api.multi
    def save(self):
        phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
        self.modify_phonecall(phonecall)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
            'params': {'in_automatic_mode': self.in_automatic_mode},
        }

    @api.multi
    def save_go_opportunity(self):
        phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
        phonecall.description = self.description
        self.modify_phonecall(phonecall)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
            'params': {'go_to_opp': True,
                       'opportunity_id': self.opportunity_id,
                       'in_automatic_mode': self.in_automatic_mode},
        }


class crm_custom_phonecall_wizard(models.TransientModel):
    _name = 'crm.custom.phonecall.wizard'

    name = fields.Char('Call summary', required=True)
    user_id = fields.Many2one('res.users', "Assign To")
    date = fields.Datetime('Date', required=True, default=lambda *a: datetime.now())
    partner_id = fields.Many2one('res.partner', "Partner")

    @api.multi
    def action_schedule(self):
        phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall_id'))
        phonecall.name = self.name
        phonecall.date = self.date
        phonecall.partner_id = self.partner_id
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_panel',
        }


class crm_phonecall_transfer_wizard(models.TransientModel):
    _name = 'crm.phonecall.transfer.wizard'

    transfer_number = fields.Char('transfer To')
    transfer_choice = fields.Selection(selection=[('physical', 'transfer to Physical Phone'), ('extern', 'transfer to an External Phone')], default='physical', required=True)

    @api.multi
    def save(self):
        if self.transfer_choice == 'extern':
            action = {
                'type': 'ir.actions.client',
                'tag': 'transfer_call',
                'params': {'number': self.transfer_number},
            }
        else:
            if self.env.user[0].sip_physicalPhone:
                action = {
                    'type': 'ir.actions.client',
                    'tag': 'transfer_call',
                    'params': {'number': self.env.user[0].sip_physicalPhone},
                }
            else:
                action = {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Wrong configuration for the call. There is no physical phone number configured"),
                    },
                }
        return action


class res_users(models.Model):
    _inherit = 'res.users'

    sip_login = fields.Char("SIP Login / Browser's Extension")
    sip_password = fields.Char('SIP Password')
    sip_physicalPhone = fields.Char("Physical Phone's Number")
    sip_always_transfert = fields.Boolean("Always redirect to physical phone", default=False)
    sip_ring_number = fields.Integer("Number of ringing", default=6, help="The number of ringing before cancelling the call")


class crm_phonecall_report(models.Model):
    _inherit = "crm.phonecall.report"

    state = fields.Selection([
        ('no_answer', 'Not Held'),
        ('cancel', 'Cancelled'),
        ('to_do', 'To Do'),
        ('done', 'Held')
    ], 'Status', readonly=True)


class crm_phonecall2phonecall(models.TransientModel):
    _inherit = "crm.phonecall2phonecall"

    date = fields.Datetime('Date', required=True)

    def action_schedule(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        phonecall = self.pool.get('crm.phonecall')
        phonecall_ids = context and context.get('active_ids') or []
        for this in self.browse(cr, uid, ids, context=context):
            phocall_ids = phonecall.schedule_another_phonecall(
                cr, uid, phonecall_ids, this.date, this.name,
                this.user_id and this.user_id.id or False,
                this.section_id and this.section_id.id or False,
                this.categ_id and this.categ_id.id or False,
                context=context)
        if self.pool.get('ir.model.data').search(cr,uid,[('module','=','crm_voip')],context=context):
            return {
                'type': 'ir.actions.client',
                'tag': 'reload_panel',
            }
        else:
            return phonecall.redirect_phonecall_view(cr, uid, phocall_ids[phonecall_ids[0]], context=context)

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        
        """
        res = super(crm_phonecall2phonecall, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        if record_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)

            categ_id = False
            data_obj = self.pool.get('ir.model.data')
            try:
                res_id = data_obj._get_id(cr, uid, 'crm', 'categ_phone2')
                categ_id = data_obj.browse(cr, uid, res_id, context=context).res_id
            except ValueError:
                pass

            if 'name' in fields:
                res.update({'name': phonecall.name})
            if 'user_id' in fields:
                res.update({'user_id': phonecall.user_id and phonecall.user_id.id or False})
            if 'date' in fields:
                res.update({'date': False})
            if 'section_id' in fields:
                res.update({'section_id': phonecall.section_id and phonecall.section_id.id or False})
            if 'categ_id' in fields:
                res.update({'categ_id': categ_id})
            if 'partner_id' in fields:
                res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
        return res
