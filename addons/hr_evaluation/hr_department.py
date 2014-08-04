# -*- encoding: utf-8 -*-

from openerp import models, fields, api


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def _interview_request_count(self):
        Interview = self.env['hr.evaluation.interview']
        for department in self:
            department.interview_request_count = Interview.search_count([
                ('user_to_review_id.department_id', '=', department.id),
                ('state', '=', 'waiting_answer')])

    @api.multi
    def _appraisal_to_start_count(self):
        Evaluation = self.env['hr_evaluation.evaluation']
        for department in self:
            department.appraisal_to_start_count = Evaluation.search_count([
                ('employee_id.department_id', '=', department.id),
                ('state', '=', 'draft')])

    appraisal_to_start_count = fields.Integer(
        compute='_appraisal_to_start_count', string='Appraisal to Start')
    interview_request_count = fields.Integer(
        compute='_interview_request_count', string='Interview Request')
