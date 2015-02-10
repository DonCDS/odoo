# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import api, models
from challenge import MAX_VISIBILITY_RANKING

class res_users_gamification_group(models.Model):
    """ Update of res.users class
        - if adding groups to an user, check gamification.challenge linked to
        this group, and the user. This is done by overriding the write method.
    """
    _inherit = 'res.users'

    @api.model
    def get_serialised_gamification_summary(self, excluded_categories=None):
        return self._serialised_goals_summary(user=self.env.user, excluded_categories=excluded_categories)

    @api.model
    def _serialised_goals_summary(self, user, excluded_categories=None):
        """Return a serialised list of goals assigned to the user, grouped by challenge
        :excluded_categories: list of challenge categories to exclude in search

        [
            {
                'id': <gamification.challenge id>,
                'name': <gamification.challenge name>,
                'visibility_mode': <visibility {ranking,personal}>,
                'currency': <res.currency id>,
                'lines': [(see gamification_challenge._get_serialized_challenge_lines() format)]
            },
        ]
        """
        all_goals_info = []
        challenge_obj = self.env['gamification.challenge']
        domain = [('user_ids', 'in', user.id), ('state', '=', 'inprogress')]
        if excluded_categories and isinstance(excluded_categories, list):
            domain.append(('category', 'not in', excluded_categories))
        for challenge in challenge_obj.search(domain):
            # serialize goals info to be able to use it in javascript
            lines = challenge._get_serialized_challenge_lines(user.id, restrict_top=MAX_VISIBILITY_RANKING)
            if lines:
                all_goals_info.append({
                    'id': challenge.id,
                    'name': challenge.name,
                    'visibility_mode': challenge.visibility_mode,
                    'currency': user.company_id.currency_id.id,
                    'lines': lines,
                })

        return all_goals_info

    @api.model
    def get_challenge_suggestions(self):
        """Return the list of challenges suggested to the user"""
        challenge_info = []
        for challenge in self.env['gamification.challenge'].search([
          ('invited_user_ids', 'in', self.env.uid), ('state', '=', 'inprogress')]):
            values = {
                'id': challenge.id,
                'name': challenge.name,
                'description': challenge.description,
            }
            challenge_info.append(values)
        return challenge_info
