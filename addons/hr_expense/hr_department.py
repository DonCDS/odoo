# -*- encoding: utf-8 -*-

from openerp import models, fields, api


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def _expense_to_approve_count(self):
        expense_data = self.env['hr.expense.expense'].read_group(
            [('department_id', 'in', self.ids), ('state', '=', 'confirm')], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in expense_data)
        for department in self:
            department.expense_to_approve_count = result.get(department.id, 0)

    expense_to_approve_count = fields.Integer(
        compute='_expense_to_approve_count', string='Expenses to Approve')
