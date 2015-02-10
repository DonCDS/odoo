# -*- coding: utf-8 -*-

from openerp import models, fields, api

class Holidays(models.Model):
    _inherit = 'hr.holidays'

    project_forecast_id = fields.Many2one('project.forecast')

    @api.multi
    def write(self, data):
        if ('state' in data):
            if (data['state'] == 'refuse' and self.project_forecast_id):
                self.project_forecast_id.unlink()
            if (data['state'] == 'confirm'):
                user_id = self.env['hr.employee'].search([('id', '=', self['employee_id'].id)], limit=1).user_id
                if (user_id):
                    new_id = self.env['project.forecast'].create({
                        'user_id': user_id.id,
                        'start_date': self['date_from'],
                        'end_date': self['date_to'],
                        'time': 100,
                        'project_id': self.get_project_id(),
                        'exclude': True,
                    })
                self.project_forecast_id = new_id.id
        if('date_from' in data or 'date_to' in data):
            dates = {}
            if ('date_from' in data): dates['start_date'] = data['date_from']
            if ('date_to' in data): dates['end_date'] = data['date_to']
            if (len(dates) > 0 and self.project_forecast_id):
                self.project_forecast_id.write(dates)
        return super(Holidays, self).write(data)

    def get_project_id(self):
        leaves_id = self.env['project.project'].search([('name', 'like', "Leaves")], limit=1)
        if (len(leaves_id) == 0):
            leaves_id = self.env['project.project'].create({
                'name': "Leaves",
                'color': 1,
            })
        return leaves_id.id
