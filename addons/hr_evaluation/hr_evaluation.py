# -*- coding: utf-8 -*-
import datetime
import time
import uuid
import urlparse
from dateutil import parser
from dateutil.relativedelta import relativedelta
from openerp import fields, api, tools, models, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF, DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.exceptions import Warning


class calendar_event(models.Model):

    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model
    def create(self, vals):
        res = super(calendar_event, self).create(vals)
        if self.env.context.get('active_model') == 'hr_evaluation.evaluation':
            evaluation = self.env['hr_evaluation.evaluation'].browse(self.env.context.get('active_id'))
            evaluation.log_meeting(res.name, res.start)
            evaluation.write({'meeting_id': res.id, 'interview_deadline': res.start_date if res.allday else res.start_datetime})
        return res


class survey_user_input(models.Model):
    _inherit = "survey.user_input"

    evaluation_id = fields.Many2one('hr_evaluation.evaluation', string='Appraisal')

    @api.multi
    def write(self, vals):
        """ Trigger the _get_total_appraisal method when user fill up the appraisal form
            and update kanban image gauge in employee evaluation.
        """
        res = super(survey_user_input, self).write(vals)
        if vals.get('state'):
            self.sudo().evaluation_id._get_total_appraisal()
        return res


class hr_evaluation(models.Model):
    _name = "hr_evaluation.evaluation"
    _inherit = ['mail.thread']
    _description = "Employee Appraisal"
    _order = 'date_close, interview_deadline'

    EVALUATION_STATE = [
        ('new', 'To Start'),
        ('pending', 'Appraisal Sent'),
        ('done', 'Done')
    ]

    @api.model
    def _set_default_template(self):
        return self.env.ref('hr_evaluation.email_template_appraisal')

    @api.one
    def _get_total_appraisal(self):
        return self.env['survey.user_input'].search([
            ('survey_id', 'in', [self.appraisal_manager_survey_id.id, self.appraisal_colleagues_survey_id.id, self.appraisal_self_survey_id.id, self.appraisal_subordinates_survey_id.id]),
            ('type', '=', 'link'), ('evaluation_id', '=', self.id)])

    @api.one
    @api.depends('state', 'interview_deadline')
    def _get_tot_sent_appraisal(self):
        for records in self._get_total_appraisal():
            self.tot_comp_appraisal = len(records)

    @api.one
    def _get_tot_completed_appraisal(self):
        for records in self._get_total_appraisal():
            self.tot_comp_appraisal = len(records.filtered(lambda r: r.state == 'done'))

    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    interview_deadline = fields.Date(string="Final Interview", select=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee')
    department_id = fields.Many2one('hr.department', string='Department')
    evaluation = fields.Text(string='Evaluation Summary', help="If the evaluation does not meet the expectations, you can propose an action plan")
    state = fields.Selection(EVALUATION_STATE, string='Status', track_visibility='onchange', required=True, readonly=True, copy=False, default='new', select=True)
    date_close = fields.Datetime(string='Appraisal Deadline', select=True, required=True)
    appraisal_manager = fields.Boolean(string='Manager')
    appraisal_manager_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_manager_rel', 'hr_evaluation_evaluation_id')
    appraisal_manager_survey_id = fields.Many2one('survey.survey', string='Manager Appraisal', required=False)
    appraisal_colleagues = fields.Boolean(string='Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', string="Employee's Appraisal")
    appraisal_self = fields.Boolean(string='Employee')
    appraisal_employee = fields.Char(string='Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
    appraisal_subordinates = fields.Boolean(string='Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'evaluation_appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', string="collaborate's Appraisal")
    color = fields.Integer(string='Color Index')
    display_name = fields.Char(compute='_set_display_name')
    mail_template = fields.Many2one('mail.template', string="Email Template For Appraisal", default=_set_default_template)
    email_to = fields.Char(string='Appraisal Receiver')
    appraisal_url = fields.Char(string='Appraisal URL')
    tot_sent_appraisal = fields.Integer(string='Number of sent appraisal', compute='_get_tot_sent_appraisal', default=0, store=True)
    tot_comp_appraisal = fields.Integer(string='Number of completed appraisal', compute="_get_tot_completed_appraisal")
    user_id = fields.Many2one('res.users', string='Related User', default=lambda self: self.env.uid)

    @api.one
    @api.depends('employee_id')
    def _set_display_name(self):
        self.display_name = self.employee_id.name_related

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id
            self.appraisal_manager = self.employee_id.appraisal_manager
            self.appraisal_manager_ids = self.employee_id.appraisal_manager_ids
            self.appraisal_manager_survey_id = self.employee_id.appraisal_manager_survey_id
            self.appraisal_colleagues = self.employee_id.appraisal_colleagues
            self.appraisal_colleagues_ids = self.employee_id.appraisal_colleagues_ids
            self.appraisal_colleagues_survey_id = self.employee_id.appraisal_colleagues_survey_id
            self.appraisal_self = self.employee_id.appraisal_self
            self.appraisal_employee = self.employee_id.appraisal_employee or self.employee_id.name
            self.appraisal_self_survey_id = self.employee_id.appraisal_self_survey_id
            self.appraisal_subordinates = self.employee_id.appraisal_subordinates
            self.appraisal_subordinates_ids = self.employee_id.appraisal_subordinates_ids
            self.appraisal_subordinates_survey_id = self.employee_id.appraisal_subordinates_survey_id

    @api.one
    @api.constrains('employee_id', 'department_id', 'date_close')
    def _check_employee_appraisal_duplication(self):
        """ Avoid duplication"""
        if self.employee_id and self.department_id and self.date_close:
            date_closed = datetime.datetime.strptime(self.date_close, DTF)
            start_datetime = time.strftime(str(date_closed.year) + '-' + str(date_closed.month) + '-01' + ' 00:00:00')
            end_datetime = time.strftime(str(date_closed.year) + '-' + str(date_closed.month) + '-' + str(date_closed.day) + ' 23:59:59')
            appraisal_ids = self.search([
                ('employee_id', '=', self.employee_id.id), ('department_id', '=', self.department_id.id),
                ('date_close', '<=', end_datetime),
                ('date_close', '>=', start_datetime)])
            if len(appraisal_ids) > 1:
                raise Warning(_("You cannot create more than one appraisal for same Month & Year"))

    @api.model
    def create_message_subscribe_users(self, subscribe_users):
        user_ids = [emp.user_id.id for emp in subscribe_users if emp.user_id]
        if self.employee_id.user_id:
            user_ids.append(self.employee_id.user_id.id)
        if self.employee_id.department_id.manager_id.user_id:
            user_ids.append(self.employee_id.department_id.manager_id.user_id.id)
        if self.employee_id.parent_id.user_id:
            user_ids.append(self.employee_id.parent_id.user_id.id)
        return self.message_subscribe_users(user_ids=user_ids)

    @api.model
    def create(self, vals):
        res = super(hr_evaluation, self.with_context(mail_create_nolog=True)).create(vals)
        if res.appraisal_manager_ids:
            res.create_message_subscribe_users(res.appraisal_manager_ids)
            res.message_post(body=_("Employee Appraisal created"), subtype="mail.mt_comment", type="notification")
        return res

    @api.multi
    def write(self, vals):
        emp_obj = self.env['hr.employee']
        for evl_rec in self:
            if self.state == 'new' and vals.get('state') == 'done':
                raise Warning(_("""Sorry ! You cannot drag this card from the "To Start" column to the "Done" column. You have to drag it to the "Appraisal Sent" column first."""))
            # avoid recursive process
            if vals.get('state') == 'pending' and not evl_rec._context.get('send_mail_status'):
                evl_rec.button_send_appraisal()
            if vals.get('interview_deadline') and self.state == 'pending' and not vals.get('meeting_id'):
                if datetime.datetime.now().strftime(DF) > vals.get('interview_deadline'):
                    raise Warning(_("The interview date can not be in the past"))
                # creating employee meeting and interview date
                evl_rec.create_update_meeting(vals)
            if vals.get('appraisal_manager_ids'):
                # add followers
                user_ids = [employee.user_id.id for employee in emp_obj.browse(vals['appraisal_manager_ids'][0][2]) if employee.user_id]
                evl_rec.message_subscribe_users(user_ids)
        return super(hr_evaluation, self).write(vals)

    @api.one
    def update_appraisal_survey_url(self, survey_url, email_to, token):
        survey_url = urlparse.urlparse(survey_url).path[1:]
        if token:
            survey_url = survey_url + '/' + token[0]
        self.appraisal_url = survey_url
        self.email_to = email_to
        return True

    @api.one
    def create_token(self, email, survey, partner_id):
        """ Create response with token """
        token = uuid.uuid4().__str__()
        self.env['survey.user_input'].create({
            'survey_id': survey.id,
            'deadline': self.date_close,
            'date_create': datetime.datetime.now().strftime(DF),
            'type': 'link',
            'state': 'new',
            'token': token,
            'evaluation_id': self.id,
            'partner_id': partner_id,
            'email': email})
        return token

    @api.multi
    def get_partner_ids(self, appraisal_receiver):
        partner_ids = []
        emp_partner_id = False
        for record in appraisal_receiver:
            for emp in record['employee_ids']:
                email = tools.email_split(emp.work_email) and tools.email_split(emp.work_email)[0] or False
                #'_find_partner_from_emails' is decorated with @api.one so here used [0][0]
                partner_id = self._find_partner_from_emails([email])[0][0] or emp.user_id.partner_id.id or None
                if partner_id:
                    if self.employee_id.id == emp.id:
                        emp_partner_id = partner_id
                    else:
                        partner_ids.append(partner_id)
                token = self.create_token(email, record['survey_id'], partner_id)
                self.update_appraisal_survey_url(record['survey_id'].public_url, email, token)
        return {'partner_ids': partner_ids, 'emp_partner_id': emp_partner_id}

    @api.one
    def send_message(self, template, partner_ids):
        mail_template_obj = self.env['mail.template']
        render_template = mail_template_obj.generate_email_batch(template, [self.id])
        self.message_post(
            body=render_template[self.id]['body'],
            model='hr_evaluation.evaluation',
            type='email',
            partner_ids=partner_ids
        )

    @api.one
    def send_survey_to_employee(self, appraisal_receiver):
        """ Create one mail by recipients and __URL__ by link with identification token """
        find_no_email = set(employee.name for record in appraisal_receiver for employee in record['employee_ids'] if not employee.work_email)
        if find_no_email:
            raise Warning(_("Following employees do not have configured an email address. \n- %s") % ('\n- ').join(find_no_email))
        res = self.get_partner_ids(appraisal_receiver)
        if res.get('emp_partner_id'):
            # Send message to employee, if employee in appraisal_receiver list.
            template = self.env['ir.model.data'].xmlid_to_res_id('hr_evaluation.email_template_appraisal_employee')
            self.send_message(template, [res['emp_partner_id']])

        self.send_message(self.mail_template.id, res.get('partner_ids'))
        if self.interview_deadline:
            self.create_update_meeting({'interview_deadline': self.interview_deadline})
        return True

    @api.one
    def button_send_appraisal(self):
        """ Changes To Start state to Appraisal Sent."""
        if self.employee_id:
            appraisal_receiver = []
            if self.appraisal_manager and self.appraisal_manager_ids:
                appraisal_receiver.append({'survey_id': self.appraisal_manager_survey_id, 'employee_ids': self.appraisal_manager_ids})
            if self.appraisal_colleagues and self.appraisal_colleagues_ids:
                appraisal_receiver.append({'survey_id': self.appraisal_colleagues_survey_id, 'employee_ids': self.appraisal_colleagues_ids})
            if self.appraisal_subordinates and self.appraisal_subordinates_ids:
                appraisal_receiver.append({'survey_id': self.appraisal_subordinates_survey_id, 'employee_ids': self.appraisal_subordinates_ids})
            if self.appraisal_self and self.appraisal_employee:
                appraisal_receiver.append({'survey_id': self.appraisal_self_survey_id, 'employee_ids': self.employee_id})
            if appraisal_receiver:
                self.send_survey_to_employee(appraisal_receiver)
            else:
                raise Warning(_("Employee do not have configured evaluation plan."))
            if self.state == 'new':
                # avoid recursive process
                self.with_context(send_mail_status=True).write({'state': 'pending'})
        return True

    @api.multi
    def button_done_appraisal(self):
        """ Changes Appraisal Sent state to Done."""
        return self.write({'state': 'done'})

    @api.multi
    def create_update_meeting(self, vals):
        """ Creates event when user enters date manually from the form view.
            If users edits the already entered date, created meeting is updated accordingly.
        """
        if self.meeting_id and self.meeting_id.allday:
            self.meeting_id.write({'start_date': vals['interview_deadline'], 'stop_date': vals['interview_deadline']})
        elif self.meeting_id and not self.meeting_id.allday:
            set_date = datetime.datetime.strptime(vals['interview_deadline'], DF).strftime(DTF)
            self.meeting_id.write({'start_datetime': set_date, 'stop_datetime': set_date})
        else:
            partner_ids = [(4, manager.user_id.partner_id.id) for manager in self.appraisal_manager_ids if manager.user_id]
            if self.employee_id.user_id:
                partner_ids.append((4, self.employee_id.user_id.partner_id.id))
            self.meeting_id = self.env['calendar.event'].create({
                'name': _('Appraisal Meeting For ') + self.employee_id.name_related,
                'start': vals['interview_deadline'],
                'stop': vals['interview_deadline'],
                'allday': True,
                'partner_ids': partner_ids,
            })
        return self.log_meeting(self.meeting_id.name, self.meeting_id.start)

    @api.multi
    def name_get(self):
        result = []
        for hr_evaluation in self:
            result.append((hr_evaluation.id, '%s' % (hr_evaluation.employee_id.name_related)))
        return result

    @api.multi
    def unlink(self):
        for appraisal in self:
            if appraisal.state != 'new':
                eva_state = dict(self.EVALUATION_STATE)
                raise Warning(_("You cannot delete appraisal which is in '%s' state") % (eva_state[appraisal.state]))
        return super(hr_evaluation, self).unlink()

    @api.v7
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            states = self.EVALUATION_STATE
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('state', '=', state_value)],
                'state': state_value,
            } for state_value, state_name in states]
            read_group_res = super(hr_evaluation, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)
            result = []
            for state_value, state_name in states:
                res = filter(lambda x: x['state'] == state_value, read_group_res)
                if not res:
                    res = filter(lambda x: x['state'] == state_value, read_group_all_states)
                result.append(res[0])
            return result
        else:
            return super(hr_evaluation, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)

    @api.multi
    def get_appraisal(self):
        sur_res_obj = self.env['survey.user_input']
        for evaluation in self:
            survey_ids = sur_res_obj.search([('survey_id', 'in', [
                evaluation.appraisal_manager_survey_id.id, evaluation.appraisal_colleagues_survey_id.id,
                evaluation.appraisal_self_survey_id.id, evaluation.appraisal_subordinates_survey_id.id]),
                ('type', '=', 'link'), ('evaluation_id', '=', evaluation.id)])
        action = self.env.ref('survey.action_survey_user_input').read()[0]
        return survey_ids, action

    @api.multi
    def get_sent_appraisal(self):
        """ Link to open sent appraisal"""
        sent_survey_ids, action = self.get_appraisal()
        sent_appraisal_ids = [sent_survey_id.id for sent_survey_id in sent_survey_ids]
        action['domain'] = str([('id', 'in', sent_appraisal_ids)])
        return action

    @api.multi
    def get_final_appraisal(self):
        """ Link to open answers appraisal"""
        result_survey_ids, action = self.get_appraisal()
        sent_appraisal_ids = [sent_survey_id.id for sent_survey_id in result_survey_ids.filtered(lambda r: r.state == 'done')]
        action['domain'] = str([('id', 'in', sent_appraisal_ids)])
        return action

    @api.multi
    def schedule_interview_date(self):
        """ Link to open calendar view for creating employee interview and meeting"""
        partner_ids = []
        for evaluation in self:
            partner_ids = [manager.user_id.partner_id.id for manager in evaluation.appraisal_manager_ids if manager.user_id]
            if evaluation.employee_id.user_id:
                partner_ids.append(evaluation.employee_id.user_id.partner_id.id)
        res = self.env.ref('calendar.action_calendar_event').read()[0]
        partner_ids.append(self.env['res.users'].browse(self._uid).partner_id.id)
        res['context'] = {
            'default_partner_ids': partner_ids
        }
        meetings = self.env['calendar.event'].search([('partner_ids', 'in', partner_ids)])
        res['domain'] = str([('id', 'in', meetings.ids)])
        return res

    @api.one
    def log_meeting(self, meeting_subject, meeting_date):
        message_receiver = []
        if self.appraisal_manager and self.appraisal_manager_ids:
            message_receiver.append({'survey_id': self.appraisal_manager_survey_id, 'employee_ids': self.appraisal_manager_ids})
        if self.appraisal_self and self.appraisal_employee:
            message_receiver.append({'survey_id': self.appraisal_self_survey_id, 'employee_ids': self.employee_id})
        partner_ids = [emp.user_id.partner_id.id for record in message_receiver for emp in record['employee_ids'] if emp.user_id]
        message = _("Subject: %s <br> Meeting scheduled at '%s'<br>") % (meeting_subject, meeting_date.split(' ')[0])
        return self.message_post(body=message, partner_ids=partner_ids)


class hr_employee(models.Model):
    _inherit = "hr.employee"

    @api.one
    def _appraisal_count(self):
        evaluation = self.env['hr_evaluation.evaluation']
        self.appraisal_count = evaluation.search_count([('employee_id', '=', self.id)])

    evaluation_date = fields.Date(string='Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_manager = fields.Boolean(string='Manager')
    appraisal_manager_ids = fields.Many2many('hr.employee', 'appraisal_manager_rel', 'hr_evaluation_evaluation_id')
    appraisal_manager_survey_id = fields.Many2one('survey.survey', string='Manager Appraisal')
    appraisal_colleagues = fields.Boolean(string='Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'appraisal_colleagues_rel', 'hr_evaluation_evaluation_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', string="Employee's Appraisal")
    appraisal_self = fields.Boolean(string='Employee')
    appraisal_employee = fields.Char(string='Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
    appraisal_subordinates = fields.Boolean(string='Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'appraisal_subordinates_rel', 'hr_evaluation_evaluation_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', string="collaborate's Appraisal")
    appraisal_repeat = fields.Boolean(string='Periodic Appraisal', default=False)
    appraisal_repeat_number = fields.Integer(string='Repeat Every', default=1)
    appraisal_repeat_delay = fields.Selection([('year', 'Year'), ('month', 'Month')], string='Repeat Every', copy=False, default='year')
    appraisal_count = fields.Integer(compute='_appraisal_count', string='Appraisal Interviews')

    @api.onchange('appraisal_manager')
    def onchange_manager_appraisal(self):
        self.appraisal_manager_ids = [self.parent_id.id]

    @api.onchange('appraisal_self')
    def onchange_self_employee(self):
        self.appraisal_employee = self.name

    @api.onchange('appraisal_colleagues')
    def onchange_colleagues(self):
        if self.department_id.id:
            self.appraisal_colleagues_ids = self.search([('department_id', '=', self.department_id.id), ('parent_id', '!=', False)])

    @api.onchange('appraisal_subordinates')
    def onchange_subordinates(self):
        self.appraisal_subordinates_ids = self.search([('parent_id', '!=', False)]).mapped('parent_id')

    @api.model
    def run_employee_evaluation(self, automatic=False, use_new_cursor=False):  # cronjob
        now = parser.parse(datetime.datetime.now().strftime(DF))
        next_date = datetime.datetime.now()
        for emp in self.search([('evaluation_date', '<=', datetime.datetime.now().strftime(DF))]):
            if emp.appraisal_repeat_delay == 'month':
                next_date = (now + relativedelta(months=emp.appraisal_repeat_number)).strftime(DF)
            else:
                next_date = (now + relativedelta(months=emp.appraisal_repeat_number * 12)).strftime(DF)
            emp.write({'evaluation_date': next_date})
            vals = {'employee_id': emp.id,
                    'date_close': datetime.datetime.now().strftime(DTF),
                    'department_id': emp.department_id.id,
                    'appraisal_manager': emp.appraisal_manager,
                    'appraisal_manager_ids': [(4, manager.id) for manager in emp.appraisal_manager_ids] or [(4, emp.parent_id.id)],
                    'appraisal_manager_survey_id': emp.appraisal_manager_survey_id.id,
                    'appraisal_colleagues': emp.appraisal_colleagues,
                    'appraisal_colleagues_ids': [(4, colleagues.id) for colleagues in emp.appraisal_colleagues_ids],
                    'appraisal_colleagues_survey_id': emp.appraisal_colleagues_survey_id.id,
                    'appraisal_self': emp.appraisal_self,
                    'appraisal_employee': emp.appraisal_employee or emp.name,
                    'appraisal_self_survey_id': emp.appraisal_self_survey_id.id,
                    'appraisal_subordinates': emp.appraisal_subordinates,
                    'appraisal_subordinates_ids': [(4, subordinates.id) for subordinates in emp.appraisal_subordinates_ids],
                    'appraisal_subordinates_survey_id': emp.appraisal_subordinates_survey_id.id}
            self.env['hr_evaluation.evaluation'].create(vals)
        return True
