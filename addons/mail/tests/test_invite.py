# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.mail.tests.common import TestMail

class test_invite(TestMail):

    def test_00_basic_invite(self):
        user_raoul = self.user_raoul
        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        mail_invite = self.env['mail.wizard.invite'].with_context({
                        'default_res_model': 'mail.group',
                        'default_res_id': self.group_pigs.id
                        }).sudo(user_raoul.id).create({
                        'partner_ids': [(4, self.partner_bert_id)],
                        'send_mail': True})
        mail_invite.with_context({'default_model': 'mail.group', 'default_res_id': 0}).sudo(user_raoul.id).add_followers()
        # Test: Pigs followers should contain Admin, Bert
        self.assertEqual(set(self.group_pigs.message_follower_ids.ids), set([self.partner_admin_id, self.partner_bert_id]), 'invite: Pigs followers after invite is incorrect')
        # Test: (pretend to) send email and check subject, body
        self.assertEqual(len(self._build_email_kwargs_list), 1, 'sent email number incorrect, should be only for Bert')
        for sent_email in self._build_email_kwargs_list:
            self.assertEqual(sent_email.get('subject'), 'Invitation to follow Discussion group: Pigs',
                'invite: subject of invitation email is incorrect')
            self.assertIn('Raoul Grosbedon invited you to follow Discussion group document: Pigs', sent_email.get('body'),
                'invite: body of invitation email is incorrect')
