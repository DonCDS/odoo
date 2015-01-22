# -*- coding: utf-8 -*-
from openerp import api, models


class PlannerProject(models.Model):

    _inherit = 'planner.planner'

    @api.model
    def _get_planner_application(self):
        planner = super(PlannerProject, self)._get_planner_application()
        planner.append(['planner_project', 'Project Planner'])
        return planner

    @api.model
    def _prepare_planner_project_data(self):
        values = {
            'prepare_backend_url': self.prepare_backend_url,
        }
        return values
