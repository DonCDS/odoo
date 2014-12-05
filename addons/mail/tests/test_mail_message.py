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
from openerp.tools import mute_logger


class TestMailMail(TestMail):

    def setUp(self):
        super(TestMailMail, self).setUp()

    def test_00_partner_find_from_email(self):
        """ Tests designed for partner fetch based on emails. """
        user_raoul, group_pigs = self.user_raoul, self.group_pigs
        # --------------------------------------------------
        # Data creation
        # --------------------------------------------------
        # 1 - Partner ARaoul
        p_a = self.ResPartner.create({'name': 'ARaoul', 'email': 'test@test.fr'})

        # --------------------------------------------------
        # CASE1: without object
        # --------------------------------------------------

        # Do: find partner with email -> first partner should be found
        partner_info = p_a.message_partner_info_from_emails(['Maybe Raoul <test@test.fr>'])[0]
        self.assertEqual(partner_info[0]['full_name'], 'Maybe Raoul <test@test.fr>',
                        'mail_thread: message_partner_info_from_emails did not handle email')
        self.assertEqual(partner_info[0]['partner_id'], p_a.id,
                        'mail_thread: message_partner_info_from_emails wrong partner found')
        # Data: add some data about partners
        # 2 - User BRaoul
        p_b = self.ResPartner.create({'name': 'BRaoul', 'email': 'test@test.fr', 'user_ids': [(4, user_raoul.id)]})
        # Do: find partner with email -> first user should be found
        partner_info = p_b.message_partner_info_from_emails(['Maybe Raoul <test@test.fr>'])[0]
        self.assertEqual(partner_info[0]['partner_id'], p_b.id,
                        'mail_thread: message_partner_info_from_emails wrong partner found')

        # --------------------------------------------------
        # CASE1: with object
        # --------------------------------------------------

        # Do: find partner in group where there is a follower with the email -> should be taken
        group_pigs.message_subscribe([p_b.id])
        partner_info = group_pigs.message_partner_info_from_emails(['Maybe Raoul <test@test.fr>'])[0]
        self.assertEqual(partner_info[0]['partner_id'], p_b.id,
                         'mail_thread: message_partner_info_from_emails wrong partner found')

class TestMailMessage(TestMail):

    def test_00_mail_message_values(self):
        """ Tests designed for testing email values based on mail.message, aliases, ... """
        user_raoul = self.user_raoul
        IrConfigParam = self.env['ir.config_parameter']
        # Data: update + generic variables
        reply_to1 = '_reply_to1@example.com'
        reply_to2 = '_reply_to2@example.com'
        email_from1 = 'from@example.com'
        alias_domain = 'schlouby.fr'
        raoul_from = 'Raoul Grosbedon <raoul@raoul.fr>'
        raoul_from_alias = 'Raoul Grosbedon <raoul@schlouby.fr>'
        raoul_reply_alias = 'YourCompany Pigs <group+pigs@schlouby.fr>'

        # --------------------------------------------------
        # Case1: without alias_domain
        # --------------------------------------------------

        IrConfigParam.search([('key', '=', 'mail.catchall.domain')]).unlink()
        # Do: free message; specified values > default values
        msg = self.MailMessage.sudo(self.user_raoul.id).create({'no_auto_thread': True, 'reply_to': reply_to1, 'email_from': email_from1})
        # Test: message content
        self.assertIn('reply_to',msg.message_id, 
                        'mail_message: message_id should be specific to a mail_message with a given reply_to')
        self.assertEqual(msg.reply_to, reply_to1,
                        'mail_message: incorrect reply_to: should come from values')
        self.assertEqual(msg.email_from, email_from1,
                        'mail_message: incorrect email_from: should come from values')
        # Do: create a mail_mail with the previous mail_message + specified reply_to
        mail = self.MailMail.sudo(self.user_raoul.id).create({'mail_message_id': msg.id, 'state': 'cancel', 'reply_to': reply_to2})
        # Test: mail_mail content
        self.assertEqual(mail.reply_to, reply_to2,
                        'mail_mail: incorrect reply_to: should come from values')
        self.assertEqual(mail.email_from, email_from1,
                        'mail_mail: incorrect email_from: should come from mail.message')
        # Do: mail_message attached to a document
        msg = self.MailMessage.sudo(self.user_raoul.id).create({'model': 'mail.group', 'res_id': self.group_pigs.id})
        # Test: message content
        self.assertIn('mail.group', msg.message_id,
                        'mail_message: message_id should contain model')
        self.assertIn('%s' % self.group_pigs.id, msg.message_id,
                        'mail_message: message_id should contain res_id')
        self.assertEqual(msg.reply_to, raoul_from,
                        'mail_message: incorrect reply_to: should be Raoul')
        self.assertEqual(msg.email_from, raoul_from,
                        'mail_message: incorrect email_from: should be Raoul')

        # -------------------------------------------------
        # Case2: with alias_domain, without catchall alias
        # -------------------------------------------------
        IrConfigParam.set_param('mail.catchall.domain', alias_domain)
        IrConfigParam.search([('key', '=', 'mail.catchall.alias')]).unlink()

        # Update message
        msg = self.MailMessage.sudo(user_raoul.id).create({'model': 'mail.group', 'res_id': self.group_pigs.id})
        # Test: generated reply_to
        self.assertEqual(msg.reply_to, raoul_reply_alias,
                        'mail_mail: incorrect reply_to: should be Pigs alias')
        # Update message: test alias on email_from
        msg = self.MailMessage.sudo(self.user_raoul.id).create({})
        # Test: generated reply_to
        self.assertEqual(msg.reply_to, raoul_from_alias,
                        'mail_mail: incorrect reply_to: should be message email_from using Raoul alias')

        # --------------------------------------------------
        # Case2: with alias_domain and  catchall alias
        # --------------------------------------------------

        IrConfigParam.set_param('mail.catchall.alias', 'gateway')
        # Update message
        msg = self.MailMessage.sudo(self.user_raoul.id).create({})
        # Test: generated reply_to
        self.assertEqual(msg.reply_to, 'YourCompany <gateway@schlouby.fr>',
            'mail_mail: reply_to should equal the catchall email alias')
        # Do: create a mail_mail
        mail = self.MailMail.create({'state': 'cancel', 'reply_to': 'someone@example.com'})
        # Test: mail_mail content
        self.assertEqual(mail.reply_to, 'someone@example.com',
            'mail_mail: reply_to should equal the rpely_to given to create')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_10_mail_message_search_access_rights(self):
        """ Testing mail_message.search() using specific _search implementation """
        group_pigs = self.group_pigs
        # Data: comment subtype for mail.message creation
        subtype_id = self.IrModelData.xmlid_to_res_id('mail.mt_comment') or False
        # Data: Birds group, private
        group_birds = self.MailGroup.create({'name': 'Birds', 'public': 'private'})
        # Data: Raoul is member of Pigs
        group_pigs.message_subscribe([self.partner_raoul_id])
        # Data: various author_ids, partner_ids, documents
        msg1 = self.MailMessage.create({'subject': '_Test', 'body': 'A', 'subtype_id': subtype_id})
        msg2 = self.MailMessage.create({'subject': '_Test', 'body': 'A+B', 'partner_ids': [(6, 0, [self.partner_bert_id])], 'subtype_id': subtype_id})
        msg3 = self.MailMessage.create({'subject': '_Test', 'body': 'A Pigs', 'model': 'mail.group', 'res_id': group_pigs.id, 'subtype_id': subtype_id})
        msg4 = self.MailMessage.create({'subject': '_Test', 'body': 'A+B Pigs', 'model': 'mail.group', 'res_id': group_pigs.id, 'partner_ids': [(6, 0, [self.partner_bert_id])], 'subtype_id': subtype_id})
        msg5 = self.MailMessage.create({'subject': '_Test', 'body': 'A+R Pigs', 'model': 'mail.group', 'res_id': group_pigs.id, 'partner_ids': [(6, 0, [self.partner_raoul_id])], 'subtype_id': subtype_id})
        msg6 = self.MailMessage.create({'subject': '_Test', 'body': 'A Birds', 'model': 'mail.group', 'res_id': group_birds.id, 'subtype_id': subtype_id})
        msg7 = self.MailMessage.sudo(self.user_raoul.id).create({'subject': '_Test', 'body': 'B', 'subtype_id': subtype_id})
        msg8 = self.MailMessage.sudo(self.user_raoul.id).create({'subject': '_Test', 'body': 'B+R', 'partner_ids': [(6, 0, [self.partner_raoul_id])], 'subtype_id': subtype_id})
        # Test: Bert: 2 messages that have Bert in partner_ids
        messages = self.MailMessage.sudo(self.user_bert.id).search([('subject', 'like', '_Test')])
        self.assertEqual(set([msg2.id, msg4.id]), set(messages.ids), 'mail_message search failed')
        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group)
        messages = self.MailMessage.sudo(self.user_raoul.id).search([('subject', 'like', '_Test'), ('body', 'like', 'A')])
        self.assertEqual(set([msg3.id, msg4.id, msg5.id]), set(messages.ids), 'mail_message search failed')
        # Test: Raoul: 3 messages on Pigs Raoul can read (employee can read group with default values), 0 on Birds (private group) + 2 messages as author
        messages = self.MailMessage.sudo(self.user_raoul.id).search([('subject', 'like', '_Test')])
        self.assertEqual(set([msg3.id, msg4.id, msg5.id, msg7.id, msg8.id]), set(messages.ids), 'mail_message search failed')
        # Test: Admin: all messages
        messages = self.MailMessage.search([('subject', 'like', '_Test')])
        self.assertEqual(set([msg1.id, msg2.id, msg3.id, msg4.id, msg5.id, msg6.id, msg7.id, msg8.id]), set(messages.ids), 'mail_message search failed')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_15_mail_message_check_access_rule(self):
        """ Testing mail_message.check_access_rule() """
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert, user_raoul = self.user_bert, self.user_raoul

        # Prepare groups: Pigs (employee), Jobs (public)
        pigs_msg_id = self.group_pigs.message_post(body='Message')
        priv_msg_id = self.group_priv.message_post(body='Message')
        # prepare an attachment
        attachment = self.IrAttachment.create({'datas': 'My attachment'.encode('base64'), 'name': 'doc.txt', 'datas_fname': 'doc.txt'})

        # ----------------------------------------
        # CASE1: read
        # ----------------------------------------

        # Do: create a new mail.message
        message = self.MailMessage.create({'body': 'My Body', 'attachment_ids': [(4, attachment.id)]})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.So we need to change all
        # except_orm to warning in mail module.)
        with self.assertRaises(except_orm):
            message.sudo(user_bert.id).read()
        # Do: message is pushed to Bert
        notifcation = self.MailNotification.create({'message_id': message.id, 'partner_id': partner_bert_id})
        # Test: Bert reads the message, ok because notification pushed
        message.sudo(user_bert.id).read()
        # Test: Bert downloads attachment, ok because he can read message
        self.MailMessage.download_attachment(message.id, attachment.id)
        # Do: remove notification
        notifcation.unlink()
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            message.sudo(user_bert.id).read()
        # Test: Bert downloads attachment, crash because he can't read message
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            self.MailMessage.sudo(user_bert.id).download_attachment(message.id, attachment.id)
        # Do: Bert is now the author
        message.write({'author_id': partner_bert_id})
        # Test: Bert reads the message, ok because Bert is the author
        message.sudo(user_bert.id).read()
        # Do: Bert is not the author anymore
        message.write({'author_id': partner_raoul_id})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            message.sudo(user_bert.id).read()
        # Do: message is attached to a document Bert can read, Jobs
        message.write({'model': 'mail.group', 'res_id': self.group_jobs.id})
        # Test: Bert reads the message, ok because linked to a doc he is allowed to read
        message.sudo(user_bert.id).read()
        # Do: message is attached to a document Bert cannot read, Pigs
        message.write({'model': 'mail.group', 'res_id': self.group_pigs.id})
        # Test: Bert reads the message, crash because not notification/not in doc followers/not read on doc
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            message.sudo(user_bert.id).read()

        # ----------------------------------------
        # CASE2: create
        # ----------------------------------------

        # Do: Bert creates a message on Pigs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.MailMessage.sudo(user_bert.id).create({'model': 'mail.group', 'res_id': self.group_pigs.id, 'body': 'Test'})
        # Do: Bert create a message on Jobs -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.MailMessage.sudo(user_bert.id).create({'model': 'mail.group', 'res_id': self.group_jobs.id, 'body': 'Test'})
        # Do: Bert create a private message -> ko, no creation rights
        with self.assertRaises(AccessError):
            self.MailMessage.sudo(user_bert.id).create({'body': 'Test'})
        # Do: Raoul creates a message on Jobs -> ok, write access to the related document
        self.MailMessage.sudo(user_raoul.id).create({'model': 'mail.group', 'res_id': self.group_jobs.id, 'body': 'Test'})
        # Do: Raoul creates a message on Priv -> ko, no write access to the related document
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            self.MailMessage.sudo(user_raoul.id).create({'model': 'mail.group', 'res_id': self.group_priv.id, 'body': 'Test'})
        # Do: Raoul creates a private message -> ok
        self.MailMessage.sudo(user_raoul.id).create({'body': 'Test'})
        # Do: Raoul creates a reply to a message on Priv -> ko
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            self.MailMessage.sudo(user_raoul.id).create({'model': 'mail.group', 'res_id': self.group_priv.id, 'body': 'Test', 'parent_id': priv_msg_id})
        # Do: Raoul creates a reply to a message on Priv-> ok if has received parent
        self.MailNotification.create({'message_id': priv_msg_id, 'partner_id': self.partner_raoul_id})
        self.MailMessage.sudo(user_raoul.id).create({'model': 'mail.group', 'res_id': self.group_priv.id, 'body': 'Test', 'parent_id': priv_msg_id})

    def test_20_message_set_star(self):
        """ Tests for starring messages and its related access rights """
        # Data: post a message on Pigs
        msg_id = self.group_pigs.message_post(body='My Body', subject='1')
        msg = self.MailMessage.browse(msg_id)
        msg_raoul = self.MailMessage.sudo(self.user_raoul.id).browse(msg_id)
        # Do: Admin stars msg
        msg.set_message_starred(True)
        # Test: notification exists
        notification = self.MailNotification.search([('partner_id', '=', self.partner_admin_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notification), 1, 'mail_message set_message_starred: more than one notification created')
        # Test: notification starred
        self.assertTrue(notification.starred, 'mail_notification starred failed')
        self.assertTrue(msg.starred, 'mail_message starred failed')
        # Do: Raoul stars msg
        msg.sudo(self.user_raoul).set_message_starred(True)
        # Test: notification exists
        notification = self.MailNotification.search([('partner_id', '=', self.partner_raoul_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notification), 1, 'mail_message set_message_starred: more than one notification created')
        # Test: notification starred
        self.assertTrue(notification.starred, 'mail_notification starred failed')
        self.assertTrue(msg_raoul.starred, 'mail_message starred failed')
        # Do: Admin unstars msg
        msg.set_message_starred(False)
        # Test: msg unstarred for Admin, starred for Raoul
        self.assertFalse(msg.starred, 'mail_message starred failed')
        self.assertTrue(msg_raoul.starred, 'mail_message starred failed')

    def test_30_message_set_read(self):
        """ Tests for reading messages and its related access rights """
        # Data: post a message on Pigs
        msg_id = self.group_pigs.message_post(body='My Body', subject='1')
        msg = self.MailMessage.browse(msg_id)
        msg_raoul = self.MailMessage.sudo(self.user_raoul.id).browse(msg_id)
        # Do: Admin reads msg
        msg.set_message_read(True)
        # Test: notification exists
        notification = self.MailNotification.search([('partner_id', '=', self.partner_admin_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notification), 1, 'mail_message set_message_read: more than one notification created')
        # Test: notification read
        self.assertTrue(notification.is_read, 'mail_notification read failed')
        self.assertFalse(msg.to_read, 'mail_message read failed')
        # Do: Raoul reads msg
        msg.sudo(self.user_raoul.id).set_message_read(True)
        # Test: notification exists
        notification = self.MailNotification.search([('partner_id', '=', self.partner_raoul_id), ('message_id', '=', msg.id)])
        self.assertEqual(len(notification), 1, 'mail_message set_message_read: more than one notification created')
        # Test: notification read
        self.assertTrue(notification.is_read, 'mail_notification starred failed')
        self.assertFalse(msg_raoul.to_read, 'mail_message starred failed')
        # Do: Admin unreads msg
        msg.set_message_read(False)
        # Test: msg unread for Admin, read for Raoul
        self.assertTrue(msg.to_read, 'mail_message read failed')
        self.assertFalse(msg_raoul.to_read, 'mail_message read failed')

    def test_40_message_vote(self):
        """ Test designed for the vote/unvote feature. """
        # Data: post a message on Pigs
        msg_id = self.group_pigs.message_post(body='My Body', subject='1')
        msg = self.MailMessage.browse(msg_id)
        msg_raoul = self.MailMessage.sudo(self.user_raoul.id).browse(msg_id)
        # Do: Admin vote for msg
        msg.vote_toggle()
        # Test: msg has Admin as voter
        self.assertEqual(set(msg.vote_user_ids.ids), set([self.user_admin.id]), 'mail_message vote: after voting, Admin should be in the voter')
        # Do: Bert vote for msg
        msg.sudo(self.user_raoul.id).vote_toggle()
        # Test: msg has Admin and Bert as voters
        self.assertEqual(set(msg_raoul.vote_user_ids.ids), set([self.user_admin.id, self.user_raoul.id]), 'mail_message vote: after voting, Admin and Bert should be in the voters')
        # Do: Admin unvote for msg
        msg.vote_toggle()
        # Test: msg has Bert as voter
        self.assertEqual(set(msg.vote_user_ids.ids), set([self.user_raoul.id]), 'mail_message vote: after unvoting, Bert should be in the voter')
        self.assertEqual(set(msg_raoul.vote_user_ids.ids), set([self.user_raoul.id]), 'mail_message vote: after unvoting, Bert should be in the voter')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_50_mail_flow_access_rights(self):
        """ Test a Chatter-looks alike flow to test access rights """
        MailComposeMessage = self.env['mail.compose.message']
        partner_bert_id, partner_raoul_id = self.partner_bert_id, self.partner_raoul_id
        user_bert, user_raoul = self.user_bert, self.user_raoul
        # Prepare groups: Pigs (employee), Jobs (public)
        pigs_msg_id = self.group_pigs.message_post(body='Message', partner_ids=[self.partner_admin_id])
        jobs_msg_id = self.group_jobs.message_post(body='Message', partner_ids=[self.partner_admin_id])

        # ----------------------------------------
        # CASE1: Bert, without groups
        # ----------------------------------------

        # Do: Bert reads Jobs basic fields, ok because public = read access on the group
        self.group_jobs.sudo(user_bert.id).read(['name', 'description'])
        # Do: Bert reads Jobs messages, ok because read access on the group => read access on its messages
        jobs_message_ids = self.group_jobs.sudo(user_bert.id).read(['message_ids'])[0]['message_ids']
        self.MailMessage.browse(jobs_message_ids).sudo(user_bert.id).read()
        bert_jobs = self.group_jobs.sudo(user_bert.id).browse()
        trigger_read = bert_jobs.name
        for message in bert_jobs.message_ids:
            trigger_read = message.subject
        for partner in bert_jobs.message_follower_ids:
            with self.assertRaises(AccessError):
                trigger_read = partner.name
        # Do: Bert comments Jobs, ko because no creation right
        with self.assertRaises(AccessError):
            self.group_jobs.sudo(user_bert.id).message_post(body='I love Pigs')
        # Do: Bert writes on its own profile, ko because no message create access
        with self.assertRaises(AccessError):
            user_bert.sudo(user_bert.id).message_post(body='I love Bert')
            partner_bert_id.sudo(user_bert.id).message_post(body='I love Bert')

        # ----------------------------------------
        # CASE2: Raoul, employee
        # ----------------------------------------

        # Do: Raoul browses Jobs -> ok, ok for message_ids, of for message_follower_ids
        raoul_jobs = self.group_jobs.sudo(user_raoul.id).browse()
        trigger_read = raoul_jobs.name
        for message in raoul_jobs.message_ids:
            trigger_read = message.subject
        for partner in raoul_jobs.message_follower_ids:
            trigger_read = partner.name
        # Do: Raoul comments Jobs, ok
        self.group_jobs.sudo(user_raoul.id).message_post(body='I love Pigs')
        # Do: Raoul create a mail.compose.message record on Jobs, because he uses the wizard
        compose = MailComposeMessage.with_context({'default_composition_mode': 'comment',
            'default_model': 'mail.group', 'default_res_id': self.group_jobs.id}
            ).sudo(user_raoul.id).create({'subject': 'Subject', 'body': 'Body text', 'partner_ids': []})
        compose.sudo(user_raoul.id).send_mail()
        # Do: Raoul replies to a Jobs message using the composer
        compose = MailComposeMessage.with_context({'default_composition_mode': 'comment',
            'default_parent_id': pigs_msg_id}).sudo(user_raoul.id).create({'subject': 'Subject', 'body': 'Body text'})
        compose.sudo(user_raoul.id).send_mail()
