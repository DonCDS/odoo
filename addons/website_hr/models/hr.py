# -*- coding: utf-8 -*-

from openerp import api, fields, models


class hr_employee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'website.published.mixin']

    public_info = fields.Text('Public Info')

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(hr_employee, self)._website_url(field_name, arg)
        res.update({(employee.id, '/page/website.aboutus#team') for employee in self})
        return res
