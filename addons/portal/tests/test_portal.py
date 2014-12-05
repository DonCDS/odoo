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
from openerp.exceptions import AccessError
from openerp.exceptions import except_orm
from openerp.tools.misc import mute_logger

class test_portal(TestMail):

    def setUp(self):
        super(test_portal, self).setUp()
        # Find Portal group
        self.group_portal_id = self.IrModelData.xmlid_to_res_id('base.group_portal')

        # Create Chell (portal user)
        self.user_chell = self.ResUsers.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.group_portal_id])]})

        self.partner_chell_id = self.user_chell.partner_id.id

        # Create a PigsPortal group
        self.group_port = self.MailGroup.with_context({'mail_create_nolog': True}).create({
            'name': 'PigsPortal',
            'public': 'groups',
            'group_public_id': self.group_portal_id})

        # Set an email address for the user running the tests, used as Sender for outgoing mails
        self.user_admin.write({'email': 'test@localhost'})

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_mail_access_rights(self):
        """ Test basic mail_message and mail_group access rights for portal users. """
        MailCompose = self.env['mail.compose.message']
        # Prepare group: Pigs and PigsPortal
        pigs_msg_id = self.group_pigs.message_post(body='Message')
        port_msg_id = self.group_port.message_post(body='Message')
        # Do: Chell browses Pigs -> ko, employee group
        chell_pigs = self.MailGroup.sudo(self.user_chell.id).browse(self.group_pigs.id)
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm)
        with self.assertRaises(except_orm):
            trigger_read = chell_pigs.name
        # Do: Chell posts a message on Pigs, crash because can not write on group or is not in the followers
        with self.assertRaises(AccessError):
            self.group_pigs.sudo(self.user_chell.id).message_post(body='Message')
        # Do: Chell is added into Pigs followers and browse it -> ok for messages, ko for partners (no read permission)
        self.group_pigs.message_subscribe_users(user_ids=[self.user_chell.id])
        chell_pigs = self.MailGroup.sudo(self.user_chell.id).browse(self.group_pigs.id)
        trigger_read = chell_pigs.name
        for message in chell_pigs.message_ids:
            trigger_read = message.subject
        for partner in chell_pigs.message_follower_ids:
            if partner.id == self.partner_chell_id:
                # Chell can read her own partner record
                continue
            # TODO Change the except_orm to Warning
            with self.assertRaises(except_orm):
                trigger_read = partner.name
        # Do: Chell comments Pigs, ok because he is now in the followers
        self.group_pigs.sudo(self.user_chell.id).message_post(body='I love Pigs')
        # Do: Chell creates a mail.compose.message record on Pigs, because he uses the wizard
        mail_compose_context = {'default_composition_mode': 'comment',
                                'default_model': 'mail.group',
                                'default_res_id': self.group_pigs.id}
        compose = MailCompose.with_context(mail_compose_context).sudo(self.user_chell.id).create({
            'subject': 'Subject',
            'body': 'Body text',
            'partner_ids': []})
        compose.sudo(self.user_chell.id).send_mail()
        mail_compose_context = {'default_composition_mode': 'comment',
                                'default_parent_id': pigs_msg_id}
        # Do: Chell replies to a Pigs message using the composer
        compose = MailCompose.with_context(mail_compose_context).sudo(self.user_chell.id).create({
                    'subject': 'Subject',
                    'body': 'Body text'})
        compose.sudo(self.user_chell.id).send_mail()
        # Do: Chell browses PigsPortal -> ok because groups security, ko for partners (no read permission)
        chell_port = self.MailGroup.sudo(self.user_chell.id).browse(self.group_port.id)
        trigger_read = chell_port.name
        for message in chell_port.message_ids:
            trigger_read = message.subject
        for partner in chell_port.message_follower_ids:
            # TODO Change the except_orm to Warning
            with self.assertRaises(except_orm):
                trigger_read = partner.name

    def test_10_mail_invite(self):
        group_pigs = self.group_pigs
        base_url = self.env['ir.config_parameter'].get_param('web.base.url', default='')
        # Carine Poilvache, with email, should receive emails for comments and emails
        partner_carine = self.ResPartner.create({'name': 'Carine Poilvache', 'email': 'c@c'})

        # Do: create a mail_wizard_invite, validate it
        self._init_mock_build_email()
        mail_invite = self.env['mail.wizard.invite'].with_context({'default_res_model': 'mail.group',
            'default_res_id': group_pigs.id}).create({
            'partner_ids': [(4, partner_carine.id)], 'send_mail': True})
        mail_invite.add_followers()
        # Test: Pigs followers should contain Admin and Bert
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([self.partner_admin_id, partner_carine.id]), 'Pigs followers after invite is incorrect')
        # Test: partner must have been prepared for signup
        self.assertTrue(partner_carine.signup_valid, 'partner has not been prepared for signup')
        self.assertTrue(base_url in partner_carine.signup_url, 'signup url is incorrect')
        self.assertTrue(self.env.cr.dbname in partner_carine.signup_url, 'signup url is incorrect')
        self.assertTrue(partner_carine.signup_token in partner_carine.signup_url, 'signup url is incorrect')
        # Test: (pretend to) send email and check subject, body
        self.assertEqual(len(self._build_email_kwargs_list), 1, 'sent email number incorrect, should be only for Bert')
        for sent_email in self._build_email_kwargs_list:
            self.assertEqual(sent_email.get('subject'), 'Invitation to follow Discussion group: Pigs',
                        'invite: subject of invitation email is incorrect')
            self.assertIn('Administrator invited you to follow Discussion group document: Pigs', sent_email.get('body'),
                        'invite: body of invitation email is incorrect')
            self.assertIn(partner_carine.signup_token, sent_email.get('body'),
                        'invite: body of invitation email does not contain signup token')

    def test_20_notification_url(self):
        """ Tests designed to test the URL added in notification emails. """
        # Partner data
        partner_raoul = self.ResPartner.browse(self.partner_raoul_id)
        partner_bert = self.ResPartner.create({'name': 'bert'})
        # Mail data
        mail = self.MailMail.create({'state': 'exception'})
        # Test: link for nobody -> None
        url = self.MailMail._get_partner_access_link(mail)
        self.assertEqual(url, None,
                        'notification email: mails not send to a specific partner should not have any URL')
        # Test: link for partner -> signup URL
        url = self.MailMail._get_partner_access_link(mail, partner=partner_bert)
        self.assertIn(partner_bert.signup_token, url,
                        'notification email: mails send to a not-user partner should contain the signup token')
        # Test: link for user -> signin
        url = self.MailMail._get_partner_access_link(mail, partner=partner_raoul)
        self.assertIn('action=mail.action_mail_redirect', url,
                        'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % partner_raoul.user_ids[0].login, url,
                        'notification email: link should contain the user login')

    @mute_logger('openerp.addons.mail.mail_thread', 'openerp.models')
    def test_21_inbox_redirection(self):
        """ Tests designed to test the inbox redirection of emails notification URLs. """
        group_pigs = self.group_pigs
        model, act_id = self.IrModelData.xmlid_to_res_model_res_id('mail.action_mail_inbox_feeds')
        model, port_act_id = self.IrModelData.xmlid_to_res_model_res_id('portal.action_mail_inbox_feeds_portal')
        # Data: post a message on pigs
        msg_id = group_pigs.message_post(body='My body', partner_ids=[self.partner_bert_id, self.partner_chell_id], type='comment', subtype='mail.mt_comment')
        # No specific parameters -> should redirect to Inbox
        action = self.MailThread.with_context({'params': {}}).sudo(self.user_raoul.id).message_redirect_action()
        self.assertEqual(action.get('type'), 'ir.actions.client',
                        'URL redirection: action without parameters should redirect to client action Inbox')
        self.assertEqual(action.get('id'), act_id,
                        'URL redirection: action without parameters should redirect to client action Inbox')
        # Bert has read access to Pigs -> should redirect to form view of Pigs
        action = self.MailThread.with_context({'params': {'message_id': msg_id}}).sudo(self.user_raoul.id).message_redirect_action()
        self.assertEqual(action.get('type'), 'ir.actions.act_window',
                        'URL redirection: action with message_id for read-accredited user should redirect to Pigs')
        self.assertEqual(action.get('res_id'), group_pigs.id,
                        'URL redirection: action with message_id for read-accredited user should redirect to Pigs')
        # Bert has no read access to Pigs -> should redirect to Inbox
        action = self.MailThread.with_context({'params': {'message_id': msg_id}}).sudo(self.user_bert.id).message_redirect_action()
        self.assertEqual(action.get('type'), 'ir.actions.client',
                        'URL redirection: action without parameters should redirect to client action Inbox')
        self.assertEqual(action.get('id'), act_id,
                        'URL redirection: action without parameters should redirect to client action Inbox')
        # Chell has no read access to pigs -> should redirect to Portal Inbox
        action = self.MailThread.with_context({'params': {'message_id': msg_id}}).sudo(self.user_chell.id).message_redirect_action()
        self.assertEqual(action.get('type'), 'ir.actions.client',
                        'URL redirection: action without parameters should redirect to client action Inbox')
        self.assertEqual(action.get('id'), port_act_id,
                        'URL redirection: action without parameters should redirect to client action Inbox')

    def test_30_message_read(self):
        group_port = self.group_port
        # Data: custom subtypes
        mt_group_public = self.MailMessageSubtype.create({'name': 'group_public', 'description': 'Group changed'})
        self.IrModelData.create({'name': 'mt_group_public', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public.id})
        # Data: post messages with various subtypes
        msg1_id = group_port.message_post(body='Body1', type='comment', subtype='mail.mt_comment')
        msg2_id = group_port.message_post(body='Body2', type='comment', subtype='mail.mt_group_public')
        msg3_id = group_port.message_post(body='Body3', type='comment', subtype='mail.mt_comment')
        msg4_id = group_port.message_post(body='Body4', type='comment')
        # msg5_id = group_port.message_post(body='Body5', type='notification')
        # Do: Chell search messages: should not see internal notes (comment without subtype)
        messages = self.MailMessage.sudo(self.user_chell.id).search([('model', '=', 'mail.group'), ('res_id', '=', group_port.id)])
        self.assertEqual(set(messages.ids), set([msg1_id, msg2_id, msg3_id]),
                        'mail_message: portal user has access to messages he should not read')
        # Do: Chell read messages she can read
        messages.sudo(self.user_chell.id).read(['body', 'type', 'subtype_id'])
        # Do: Chell read a message she should not be able to read
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            self.MailMessage.browse(msg4_id).sudo(self.user_chell.id).read(['body', 'type', 'subtype_id'])
