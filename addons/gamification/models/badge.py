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

from openerp import api, fields, models, SUPERUSER_ID
from openerp.tools.translate import _

import logging
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class gamification_badge_user(models.Model):
    """User having received a badge"""

    _name = 'gamification.badge.user'
    _description = 'Gamification user badge'
    _order = "create_date desc"
    _rec_name = "badge_name"


    user_id = fields.Many2one('res.users', string="User", required=True, ondelete="cascade")
    sender_id = fields.Many2one('res.users', string="Sender", help="The user who has send the badge")
    badge_id = fields.Many2one('gamification.badge', string='Badge', required=True, ondelete="cascade")
    challenge_id = fields.Many2one('gamification.challenge', string='Challenge originating',
        help="If this badge was rewarded through a challenge")
    comment = fields.Text('Comment')
    badge_name = fields.Char('Badge Name', related=badge_id.name)


    @api.multi
    def _send_badge(self):
        """Send a notification to a user for receiving a badge

        Does not verify constrains on badge granting.
        The users are added to the owner_ids (create badge_user if needed)
        The stats counters are incremented
        :param ids: list(int) of badge users that will receive the badge
        """
        res = True
        template_received = self.env.ref('gamification.email_template_badge_received')[1]
        for badge_user in self:
            template = self.env['mail.template'].get_email_template(template_received.id, badge_user.id)
            body_html = template.render_template(template.body_html, 'gamification.badge.user', badge_user.id)
            res = badge_user.user_ids.message_post(
                body=body_html,
                subtype='gamification.mt_badge_granted',
                partner_ids=[badge_user.user_id.partner_id.id])
        return res

    @api.model
    def create(self, vals):
        self.env['gamification.badge'].browse(vals['badge_id']).check_granting()
        return super(gamification_badge_user, self).create(vals)


class gamification_badge(models.Model):
    """Badge object that users can send and receive"""

    CAN_GRANT = 1
    NOBODY_CAN_GRANT = 2
    USER_NOT_VIP = 3
    BADGE_REQUIRED = 4
    TOO_MANY = 5

    _name = 'gamification.badge'
    _description = 'Gamification badge'
    _inherit = ['mail.thread']

    def _get_owners_info(self):
        """Return:
            the list of unique res.users ids having received this badge
            the total number of time this badge was granted
            the total number of users this badge was granted to
        """
        result = dict((res_id, {'stat_count': 0, 'stat_count_distinct': 0, 'unique_owner_ids': []}) for res_id in self.ids)

        self.cr.execute("""
            SELECT badge_id, count(user_id) as stat_count,
                count(distinct(user_id)) as stat_count_distinct,
                array_agg(distinct(user_id)) as unique_owner_ids
            FROM gamification_badge_user
            WHERE badge_id in %s
            GROUP BY badge_id
            """, (tuple(self.ids),))
        for (badge_id, stat_count, stat_count_distinct, unique_owner_ids) in self.env.cr.fetchall():
            result[badge_id] = {
                'stat_count': stat_count,
                'stat_count_distinct': stat_count_distinct,
                'unique_owner_ids': unique_owner_ids,
            }
        return result

    def _get_badge_user_stats(self):
        """Return stats related to badge users"""
        result = {}
        badge_user_obj = self.env['gamification.badge.user']
        today = fields.Date.from_string(fields.Date.context_today(self))
        first_month_day = fields.Date.to_string(today.replace(day=1))
        for badge in self:
            result[badge.id] = {
                'stat_my': badge_user_obj.search_count([('badge_id', '=', badge.id), ('user_id', '=', self.env.uid)]),
                'stat_this_month': badge_user_obj.search_count([('badge_id', '=', badge.id), ('create_date', '>=', first_month_day)]),
                'stat_my_this_month': badge_user_obj.search_count([('badge_id', '=', badge.id), ('user_id', '=', self.env.uid), ('create_date', '>=', first_month_day)]),
                'stat_my_monthly_sending': badge_user_obj.search_count([('badge_id', '=', badge.id), ('create_uid', '=', self.env.uid), ('create_date', '>=', first_month_day)])
            }
        return result

    def _remaining_sending_calc(self):
        """Computes the number of badges remaining the user can send

        0 if not allowed or no remaining
        integer if limited sending
        -1 if infinite (should not be displayed)
        """
        result = {}
        for badge in self:
            if badge._can_grant_badge() != 1:
                # if the user cannot grant this badge at all, result is 0
                result[badge.id] = 0
            elif not badge.rule_max:
                # if there is no limitation, -1 is returned which means 'infinite'
                result[badge.id] = -1
            else:
                result[badge.id] = badge.rule_max_number - badge.stat_my_monthly_sending
        return result

    name = fields.Char('Badge', required=True, translate=True)
    description = fields.Text('Description')
    image = fields.Binary("Image", help="This field holds the image used for the badge, limited to 256x256"),
    rule_auth = fields.Selection([
            ('everyone', 'Everyone'),
            ('users', 'A selected list of users'),
            ('having', 'People having some badges'),
            ('nobody', 'No one, assigned through challenges'),
        ],
        string="Allowance to Grant",
        help="Who can grant this badge",
        required=True, default='everyone')
    rule_auth_user_ids = fields.Many2many('res.users', 'rel_badge_auth_users',
            string='Authorized Users',
            help="Only these people can give this badge")
    rule_auth_badge_ids = fields.Many2many('gamification.badge',
            'gamification_badge_rule_badge_rel', 'badge1_id', 'badge2_id',
            string='Required Badges',
            help="Only the people having these badges can give this badge")
    rule_max = fields.Boolean('Monthly Limited Sending',
        help="Check to set a monthly limit per person of sending this badge")
    rule_max_number = fields.Integer('Limitation Number',
        help="The maximum number of time this badge can be sent per month per person.")
    stat_my_monthly_sending = fields.Integer(compute=_get_badge_user_stats,
        string='My Monthly Sending Total',
        help="The number of time the current user has sent this badge this month.")

    remaining_sending = fields.Interger(compute=_remaining_sending_calc,
        string='Remaining Sending Allowed', help="If a maxium is set")

    challenge_ids = fields.One2many('gamification.challenge', 'reward_id',
        string="Reward of Challenges")
    goal_definition_ids = fields.Many2many('gamification.goal.definition', 'badge_unlocked_definition_rel',
        string='Rewarded by',
        help="The users that have succeeded theses goals will receive automatically the badge.")
    owner_ids = fields.One2many('gamification.badge.user', 'badge_id',
        string='Owners', help='The list of instances of this badge granted to users')
    active = fields.Boolean(default=True)
    unique_owner_ids = fields.Many2many(compute=_get_owners_info,
        string='Unique Owners',
        help="The list of unique users having received this badge.",
        relation="res.users")
    stat_count = fields.Integer(compute=_get_owners_info, string='Total',
        help="The number of time this badge has been received.")
    stat_count_distinct = fields.Integer(compute=_get_owners_info,
        string='Number of users',
        help="The number of time this badge has been received by unique users."),
    stat_this_month = fields.Integer(compute=_get_badge_user_stats,
        string='Monthly total',
        help="The number of time this badge has been received this month.")
    stat_my = fields.Integer(compute=_get_badge_user_stats, string='My Total',
        help="The number of time the current user has received this badge.")
    stat_my_this_month = fields.Integer(compute=_get_badge_user_stats,
        string='My Monthly Total',
        help="The number of time the current user has received this badge this month.")

    @api.one
    def check_granting(self):
        """Check the current user can grant the badge and raise the appropriate exception
        if not

        Do not check for SUPERUSER_ID
        """
        status_code = self._can_grant_badge()
        if status_code == self.CAN_GRANT:
            return True
        elif status_code == self.NOBODY_CAN_GRANT:
            raise UserError(_('This badge can not be sent by users.'))
        elif status_code == self.USER_NOT_VIP:
            raise UserError(_('You are not in the user allowed list.'))
        elif status_code == self.BADGE_REQUIRED:
            raise UserError(_('You do not have the required badges.'))
        elif status_code == self.TOO_MANY:
            raise UserError(_('You have already sent this badge too many time this month.'))
        else:
            _logger.exception("Unknown badge status code: %d" % int(status_code))
        return False

    @api.one
    def _can_grant_badge(self):
        """Check if a user can grant a badge to another user

        :return: integer representing the permission.
        """
        if self.env.uid == SUPERUSER_ID:
            return self.CAN_GRANT

        if self.rule_auth == 'nobody':
            return self.NOBODY_CAN_GRANT

        elif self.rule_auth == 'users' and self.env.uid not in [user.id for user in self.rule_auth_user_ids]:
            return self.USER_NOT_VIP

        elif self.rule_auth == 'having':
            all_user_badges = self.env['gamification.badge.user'].search([('user_id', '=', self.env.uid)])
            for required_badge in self.rule_auth_badge_ids:
                if required_badge not in all_user_badges:
                    return self.BADGE_REQUIRED

        if self.rule_max and self.stat_my_monthly_sending >= self.rule_max_number:
            return self.TOO_MANY

        # badge.rule_auth == 'everyone' -> no check
        return self.CAN_GRANT

    @api.model
    def check_progress(self):
        badge = self.env.ref('gamification.badge_hidden', False)
        if not badge:
            return True
        badge_user_obj = self.env['gamification.badge.user']
        if not badge_user_obj.search([('user_id', '=', self.env.uid), ('badge_id', '=', badge.id)]):
            badge_user_obj.sudo().create({
                'user_id': self.env.uid,
                'badge_id': badge.id,
            })
        return True
