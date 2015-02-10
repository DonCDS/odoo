# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import ValidationError
from datetime import datetime, timedelta

class project_forecast(models.Model):
    _name = 'project.forecast'

    def default_user_id(self):
        return self.env.user if ("default_user_id" not in self.env.context) else self.env.context["default_user_id"]

    def default_end_date(self):
        today = fields.Date.from_string(fields.Datetime.now())
        duration = timedelta(days=1)
        return today+duration
    
    name = fields.Char(compute='_get_name')

    user_id = fields.Many2one('res.users', string="User", required=True,
                              default=default_user_id)
    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2one('project.task', string="Task")

    time = fields.Integer(string="%", default=100.0, help="Percentage of working time")

    start_date = fields.Datetime(default=fields.Date.today, required="True")
    end_date = fields.Datetime(default=default_end_date, required="True")

    # used by the gantt view
    project_start_date = fields.Datetime(compute="_get_project_start_date")
    project_end_date = fields.Datetime(compute="_get_project_end_date")
    task_start_date = fields.Datetime(compute="_get_task_start_date")
    task_end_date = fields.Datetime(compute="_get_task_end_date")

    # consolidation color and exclude
    color = fields.Integer(string="Color", compute='_get_color')
    exclude = fields.Boolean(string="Exclude", compute='_get_exclude', store=True)
    
    # resource
    resource_hours = fields.Float(string="Planned hours", compute='_get_resource_hours', store=True)
    effective_hours = fields.Float(string="Effective hours", compute='_get_effective_hours', store=True)
    percentage_hours = fields.Float(string="Progress", compute='_get_percentage_hours', store=True)
    
    @api.one
    @api.depends('project_id', 'task_id', 'user_id')
    def _get_name(self):
        group = self.env.context["group_by"] if "group_by" in self.env.context else ""

        name = []
        if (group != "user_id"): name.append(self.user_id.name)
        if (group != "project_id" and self.project_id): name.append(self.project_id.name)
        if (group != "task_id" and self.task_id): name.append(self.task_id.name)
        self.name = " - ".join(name)
        if (self.name == ""): self.name = "undefined"
        
    @api.one
    @api.depends('project_id.date_start')
    def _get_project_start_date(self):
        self.project_start_date = self.project_id.date_start if (self.project_id) else ""
        
    @api.one
    @api.depends('project_id.date')
    def _get_project_end_date(self):
        self.project_end_date = self.project_id.date if (self.project_id) else ""
 
    @api.one
    @api.depends('task_id.date_start')
    def _get_task_start_date(self):
        self.task_start_date = self.task_id.date_start if (self.task_id) else ""
 
    @api.one
    @api.depends('task_id.date_end')
    def _get_task_end_date(self):
        self.task_end_date = self.task_id.date_end if (self.task_id) else ""

    @api.one
    @api.depends('project_id.color')
    def _get_color(self):
        if (self.project_id):
            self.color = self.project_id.color
        else:
            self.color = 0

    @api.one
    @api.depends('project_id.name')
    def _get_exclude(self):
        self.exclude = (self.project_id and self.project_id.name == "Leaves")

    @api.one
    @api.depends('time', 'start_date', 'end_date')
    def _get_resource_hours(self):
        start = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M:%S")
        stop = datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
        resource = self.env['resource.resource'].search([('user_id', '=', self.user_id.id)], limit=1)
        if (resource):
            calendar = resource.calendar_id
            if (calendar):
                hours = calendar.get_working_hours(start, stop)
                self.resource_hours = hours[0]*(self.time/100.0)
                return
        self.resource_hours = 0
        
    @api.one
    @api.depends('task_id', 'user_id', 'start_date', 'end_date', 'project_id.analytic_account_id')
    def _get_effective_hours(self):
        if (self.task_id):
            works = self.env['project.task.work'].search([('task_id', '=', self.task_id.id), ('user_id', '=', self.user_id.id), ('date', '>=', self.start_date), ('date', '<=', self.end_date)])
            acc = 0
            for work in works:
                acc += work.hours
            self.effective_hours = acc
        elif(self.project_id):
            timesheets = self.env['account.analytic.line'].search([('account_id', '=', self.project_id.analytic_account_id.id), ('user_id', '=', self.user_id.id), ('date', '>=', self.start_date), ('date', '<=', self.end_date)])
            acc = 0
            for timesheet in timesheets:
                acc += timesheet.unit_amount
            self.effective_hours = acc
            
        else:
            self.effective_hours = 0

    @api.one
    @api.depends('resource_hours', 'effective_hours')
    def _get_percentage_hours(self):
        if (self.resource_hours != 0):
            self.percentage_hours = self.effective_hours / self.resource_hours
        else:
            self.percentage_hours = 0
        
    @api.one
    @api.constrains('time')
    def _check_time_positive(self):
        if self.time and (self.time < 0):
            raise ValidationError("The time must be positive")
    
    @api.one
    @api.constrains('task_id', 'project_id')
    def _task_id_in_project(self):
        if self.project_id and self.task_id and (self.task_id not in self.project_id.tasks):
            raise ValidationError("Your task is not in the selected project.")

    @api.one
    @api.constrains('start_date', 'end_date')
    def _start_date_lower_end_date(self):
        if self.start_date > self.end_date:
            raise ValidationError("The start-date must be lower than end-date.")

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if (self.task_id): self.project_id = self.task_id.project_id

    @api.onchange('project_id')
    def _onchange_project_id(self):
        domain = [] if not self.project_id else [('project_id', '=', self.project_id.id)]
        return {
            'domain': { 'task_id': domain },
        }

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if (self.end_date < self.start_date):
            start = fields.Date.from_string(self.start_date)
            duration = timedelta(days=1)
            self.end_date = start + duration

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if (self.start_date > self.end_date):
            end = fields.Date.from_string(self.end_date)
            duration = timedelta(days=1)
            self.start_date = end - duration
       
class project(models.Model):
    _name = 'project.project'
    _inherit = 'project.project'

    allow_forecast = fields.Boolean('Allow forecast', default=False, help="This feature shows the Forecast link in the kanban view")
