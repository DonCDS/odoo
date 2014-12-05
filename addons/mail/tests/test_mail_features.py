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
from openerp.tools import mute_logger, email_split
from openerp.tools.mail import html_sanitize

class test_mail(TestMail):

    def test_000_alias_setup(self):
        """ Test basic mail.alias setup works, before trying to use them for routing """
        self.user_valentin = self.ResUsers.create({'name': 'Valentin Cognito', 'email': 'valentin.cognito@gmail.com',
            'login': 'valentin.cognito', 'alias_name': 'valentin.cognito'})
        self.assertEquals(self.user_valentin.alias_name, self.user_valentin.login, "Login should be used as alias")
        self.user_pagan = self.ResUsers.create({'name': 'Pagan Le Marchant', 'email': 'plmarchant@gmail.com',
            'login': 'plmarchant@gmail.com', 'alias_name': 'plmarchant@gmail.com'})
        self.assertEquals(self.user_pagan.alias_name, 'plmarchant', "If login is an email, the alias should keep only the local part")
        self.user_barty = self.ResUsers.create({'name': 'Bartholomew Ironside', 'email': 'barty@gmail.com',
            'login': 'b4r+_#_R3wl$$', 'alias_name': 'b4r+_#_R3wl$$'})
        self.assertEquals(self.user_barty.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_00_followers_function_field(self):
        """ Tests designed for the many2many function field 'follower_ids'.
            We will test to perform writes using the many2many commands 0, 3, 4,
            5 and 6. """
        user_admin, partner_bert_id, group_pigs = self.user_admin, self.partner_bert_id, self.group_pigs
        # Data: create 'disturbing' values in mail.followers: same res_id, other res_model; same res_model, other res_id
        group_dummy = self.MailGroup.with_context({'mail_create_nolog': True}).create({'name': 'Dummy group'})
        self.MailFollowers.create({'res_model': 'mail.thread', 'res_id': self.group_pigs.id, 'partner_id': partner_bert_id})
        self.MailFollowers.create({'res_model': 'mail.group', 'res_id': group_dummy.id, 'partner_id': partner_bert_id})
        # Pigs just created: should be only Admin as follower
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([user_admin.partner_id.id]), 'Admin should be the only Pigs fan')
        # Subscribe Bert through a '4' command
        group_pigs.write({'message_follower_ids': [(4, partner_bert_id)]})
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the only Pigs fans')
        # Unsubscribe Bert through a '3' command
        group_pigs.write({'message_follower_ids': [(3, partner_bert_id)]})
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([user_admin.partner_id.id]), 'Admin should be the only Pigs fan')
        # Set followers through a '6' command
        group_pigs.write({'message_follower_ids': [(6, 0, [partner_bert_id])]})
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([partner_bert_id]), 'Bert should be the only Pigs fan')
        # Add a follower created on the fly through a '0' command
        group_pigs.write({'message_follower_ids': [(0, 0, {'name': 'Patrick Fiori'})]})
        partner_patrick = self.ResPartner.search([('name', '=', 'Patrick Fiori')], limit=1)
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([partner_bert_id, partner_patrick.id]), 'Bert and Patrick should be the only Pigs fans')
        # Finally, unlink through a '5' command
        group_pigs.write({'message_follower_ids': [(5, 0)]})
        self.assertFalse(set(group_pigs.message_follower_ids.ids), 'Pigs group should not have fans anymore')
        # Test dummy data has not been altered
        followers = self.MailFollowers.search([('res_model', '=', 'mail.thread'), ('res_id', '=', group_pigs.id)])
        follower_ids = set([follower.partner_id.id for follower in followers])
        self.assertEqual(follower_ids, set([partner_bert_id]), 'Bert should be the follower of dummy mail.thread data')
        followers = self.MailFollowers.search([('res_model', '=', 'mail.group'), ('res_id', '=', group_dummy.id)])
        follower_ids = set([follower.partner_id.id for follower in followers])
        self.assertEqual(follower_ids, set([partner_bert_id, user_admin.partner_id.id]), 'Bert and Admin should be the followers of dummy mail.group data')

    def test_05_message_followers_and_subtypes(self):
        """ Tests designed for the subscriber API as well as message subtypes """
        user_admin, user_raoul, group_pigs = self.user_admin, self.user_raoul, self.group_pigs
        # Data: message subtypes
        self.MailMessageSubtype.create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.group'})
        self.MailMessageSubtype.create({'name': 'mt_other_def', 'default': True, 'res_model': 'crm.lead'})
        self.MailMessageSubtype.create({'name': 'mt_all_def', 'default': True, 'res_model': False})
        mt_mg_nodef = self.MailMessageSubtype.create({'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.group'})
        mt_all_nodef = self.MailMessageSubtype.create({'name': 'mt_all_nodef', 'default': False, 'res_model': False})
        default_group_subtypes = self.MailMessageSubtype.search([('default', '=', True), '|', ('res_model', '=', 'mail.group'), ('res_model', '=', False)])

        # ----------------------------------------
        # CASE1: test subscriptions with subtypes
        # ----------------------------------------

        # Do: subscribe Raoul, should have default subtypes
        group_pigs.message_subscribe_users(user_ids=[user_raoul.id])
        # Test: 2 followers (Admin and Raoul)
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]),
                        'message_subscribe: Admin and Raoul should be the only 2 Pigs fans')
        # Raoul follows default subtypes
        follower = self.MailFollowers.search([
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', group_pigs.id),
                        ('partner_id', '=', user_raoul.partner_id.id)], limit=1)
        self.assertEqual(set(follower.subtype_ids.ids), set(default_group_subtypes.ids),
                        'message_subscribe: Raoul subscription subtypes are incorrect, should be all default ones')
        # Do: subscribe Raoul with specified new subtypes
        group_pigs.sudo(user_raoul.id).message_subscribe_users(subtype_ids=[mt_mg_nodef.id])
        # Test: 2 followers (Admin and Raoul)
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]),
                        'message_subscribe: Admin and Raoul should be the only 2 Pigs fans')
        # Test: 2 lines in mail.followers (no duplicate for Raoul)
        no_of_fol = self.MailFollowers.search_count([
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', group_pigs.id)])
        self.assertEqual(no_of_fol, 2,
                        'message_subscribe: subscribing an already-existing follower should not create new entries in mail.followers')
        # Test: Raoul follows only specified subtypes
        follower = self.MailFollowers.search([
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', group_pigs.id),
                        ('partner_id', '=', user_raoul.partner_id.id)], limit=1)
        self.assertEqual(set(follower.subtype_ids.ids), set([mt_mg_nodef.id]),
                        'message_subscribe: Raoul subscription subtypes are incorrect, should be only specified')
        # Do: Subscribe Raoul without specified subtypes: should not erase existing subscription subtypes
        group_pigs.message_subscribe_users(user_ids=[user_raoul.id, user_raoul.id])
        group_pigs.message_subscribe_users(user_ids=[user_raoul.id])
        # Test: 2 followers (Admin and Raoul)
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([user_raoul.partner_id.id, user_admin.partner_id.id]),
                        'message_subscribe: Admin and Raoul should be the only 2 Pigs fans')
        # Test: Raoul follows default subtypes
        follower = self.MailFollowers.search([
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', group_pigs.id),
                        ('partner_id', '=', user_raoul.partner_id.id)], limit=1)
        self.assertEqual(set(follower.subtype_ids.ids), set([mt_mg_nodef.id]),
                        'message_subscribe: Raoul subscription subtypes are incorrect, should be only specified')
        # Do: Unsubscribe Raoul twice through message_unsubscribe_users
        group_pigs.message_unsubscribe_users([user_raoul.id, user_raoul.id])

        # Test: 1 follower (Admin)
        self.assertEqual(group_pigs.message_follower_ids.ids, [user_admin.partner_id.id], 'Admin must be the only Pigs fan')
        # Test: 1 lines in mail.followers (no duplicate for Raoul)
        no_of_fol = self.MailFollowers.search_count([
                        ('res_model', '=', 'mail.group'),
                        ('res_id', '=', group_pigs.id)])
        self.assertEqual(no_of_fol, 1,
                        'message_subscribe: group should have only 1 entry in mail.follower for 1 follower')
        # Do: subscribe Admin with subtype_ids
        group_pigs.message_subscribe_users(user_ids=[self.env.uid],subtype_ids=[mt_mg_nodef.id, mt_all_nodef.id])
        follower = self.MailFollowers.search([('res_model', '=', 'mail.group'), ('res_id', '=', group_pigs.id), ('partner_id', '=', user_admin.partner_id.id)], limit=1)
        self.assertEqual(set(follower.subtype_ids.ids), set([mt_mg_nodef.id, mt_all_nodef.id]), 'subscription subtypes are incorrect')

        # ----------------------------------------
        # CASE2: test mail_thread fields
        # ----------------------------------------

        subtype_data = group_pigs._get_subscription_data(None, None)[group_pigs.id]['message_subtype_data']
        self.assertEqual(set(subtype_data.keys()), set(['Discussions', 'mt_mg_def', 'mt_all_def', 'mt_mg_nodef', 'mt_all_nodef']), 'mail.group available subtypes incorrect')
        self.assertFalse(subtype_data['Discussions']['followed'], 'Admin should not follow Discussions in pigs')
        self.assertTrue(subtype_data['mt_mg_nodef']['followed'], 'Admin should follow mt_mg_nodef in pigs')
        self.assertTrue(subtype_data['mt_all_nodef']['followed'], 'Admin should follow mt_all_nodef in pigs')

    def test_11_notification_url(self):
        """ Tests designed to test the URL added in notification emails. """
        group_pigs = self.group_pigs
        # Test URL formatting
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # Partner data
        partner_raoul = self.ResPartner.browse(self.partner_raoul_id)
        partner_bert =  self.ResPartner.create({'name': 'bert'})
        # Mail data
        mail = self.MailMail.create({'state': 'exception'})
        # Test: link for nobody -> None
        url = self.MailMail._get_partner_access_link(mail)
        self.assertEqual(url, None,
                        'notification email: mails not send to a specific partner should not have any URL')
        # Test: link for partner -> None
        url = self.MailMail._get_partner_access_link(mail, partner_bert)
        self.assertEqual(url, None,
                        'notification email: mails send to a not-user partner should not have any URL')
        # Test: link for user -> signin
        url = self.MailMail._get_partner_access_link(mail, partner_raoul)
        self.assertIn(base_url, url,
                        'notification email: link should contain web.base.url')
        self.assertIn('db=%s' % self.env.cr.dbname, url,
                        'notification email: link should contain database name')
        self.assertIn('action=mail.action_mail_redirect', url,
                        'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % partner_raoul.user_ids[0].login, url,
                        'notification email: link should contain the user login')
        # Test: link for user -> with model and res_id
        mail= self.MailMail.create({'model': 'mail.group', 'res_id': group_pigs.id})
        url = self.MailMail._get_partner_access_link(mail, partner_raoul)
        self.assertIn(base_url, url,
                        'notification email: link should contain web.base.url')
        self.assertIn('db=%s' % self.env.cr.dbname, url,
                        'notification email: link should contain database name')
        self.assertIn('action=mail.action_mail_redirect', url,
                        'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % partner_raoul.user_ids[0].login, url,
                        'notification email: link should contain the user login')
        self.assertIn('model=mail.group', url,
                        'notification email: link should contain the model when having not notification email on a record')
        self.assertIn('res_id=%s' % group_pigs.id, url,
                        'notification email: link should contain the res_id when having not notification email on a record')
        # Test: link for user -> with model and res_id
        mail = self.MailMail.create({'notification': True, 'model': 'mail.group', 'res_id': group_pigs.id})
        url =  self.MailMail._get_partner_access_link(mail, partner_raoul)
        self.assertIn(base_url, url,
                        'notification email: link should contain web.base.url')
        self.assertIn('db=%s' % self.env.cr.dbname, url,
                        'notification email: link should contain database name')
        self.assertIn('action=mail.action_mail_redirect', url,
                        'notification email: link should contain the redirect action')
        self.assertIn('login=%s' % partner_raoul.user_ids[0].login, url,
                        'notification email: link should contain the user login')
        self.assertIn('message_id=%s' % mail.mail_message_id.id, url,
                        'notification email: link based on message should contain the mail_message id')
        self.assertNotIn('model=mail.group', url,
                        'notification email: link based on message should not contain model')
        self.assertNotIn('res_id=%s' % group_pigs.id, url,
                        'notification email: link based on message should not contain res_id')

    @mute_logger('openerp.addons.mail.mail_thread', 'openerp.models')
    def test_12_inbox_redirection(self):
        """ Tests designed to test the inbox redirection of emails notification URLs. """
        group_pigs = self.group_pigs
        model, act_id = self.IrModelData.xmlid_to_res_model_res_id('mail.action_mail_inbox_feeds')
        # Data: post a message on pigs
        msg_id = self.group_pigs.message_post(body='My body', partner_ids=[self.partner_bert_id], type='comment', subtype='mail.mt_comment')
        # No specific parameters -> should redirect to Inbox
        action = self.MailThread.with_context({'params': {}}).sudo(self.user_raoul.id).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.client',
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        self.assertEqual(
            action.get('id'), act_id,
            'URL redirection: action without parameters should redirect to client action Inbox'
        )

        # Raoul has read access to Pigs -> should redirect to form view of Pigs
        action = self.MailThread.with_context({'params': {'message_id': msg_id}}).sudo(
            self.user_raoul.id).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.act_window',
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )
        self.assertEqual(
            action.get('res_id'), group_pigs.id,
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )
        action = self.MailThread.with_context({'params': {'model': 'mail.group', 'res_id': group_pigs.id}}).sudo(
            self.user_raoul.id).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.act_window',
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )
        self.assertEqual(
            action.get('res_id'), group_pigs.id,
            'URL redirection: action with message_id for read-accredited user should redirect to Pigs'
        )

        # Bert has no read access to Pigs -> should redirect to Inbox
        action = self.MailThread.with_context({'params': {'message_id': msg_id}}).sudo(
            self.user_bert.id).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.client',
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        self.assertEqual(
            action.get('id'), act_id,
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        action = self.MailThread.with_context({'params': {'model': 'mail.group', 'res_id': group_pigs.id}}).sudo(
            self.user_bert.id).message_redirect_action()
        self.assertEqual(
            action.get('type'), 'ir.actions.client',
            'URL redirection: action without parameters should redirect to client action Inbox'
        )
        self.assertEqual(
            action.get('id'), act_id,
            'URL redirection: action without parameters should redirect to client action Inbox'
        )

    def test_20_message_post(self):
        """ Tests designed for message_post. """
        user_raoul, group_pigs = self.user_raoul, self.group_pigs
        # --------------------------------------------------
        # Data creation
        # --------------------------------------------------
        # 0 - Update existing users-partners
        self.user_admin.write({'email': 'a@a', 'notify_email': 'always'})
        self.user_raoul.write({'email': 'r@r'})
        # 1 - Bert Tartopoils, with email, should for comments and emails
        p_b = self.ResPartner.create({'name': 'Bert Tartopoils', 'email': 'b@b'})
        # 2 - Carine Poilvache, with email, should receive emails for emails
        p_c = self.ResPartner.create({'name': 'Carine Poilvache', 'email': 'c@c', 'notify_email': 'none'})
        # 3 - Dédé Grosbedon, without email, to test email verification; should receive emails for every message
        p_d = self.ResPartner.create({'name': 'Dédé Grosbedon', 'email': 'd@d', 'notify_email': 'always'})
        # 4 - Attachments
        attach1 = self.IrAttachment.sudo(user_raoul.id).create({
            'name': 'Attach1', 'datas_fname': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        attach2 = self.IrAttachment.sudo(user_raoul.id).create({
            'name': 'Attach2', 'datas_fname': 'Attach2',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        attach3 = self.IrAttachment.sudo(user_raoul.id).create({
            'name': 'Attach3', 'datas_fname': 'Attach3',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        # 5 - Mail data
        _subject = 'Pigs'
        _mail_subject = 'Re: %s' % (group_pigs.name)
        _body1 = '<p>Pigs rules</p>'
        _body2 = '<html>Pigs rocks</html>'
        _attachments = [
            ('List1', 'My first attachment'),
            ('List2', 'My second attachment')
        ]

        # --------------------------------------------------
        # CASE1: post comment + partners + attachments
        # --------------------------------------------------

        # Data: set alias_domain to see emails with alias
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        # Data: change Pigs name to test reply_to
        self.group_pigs.write({'name': '"Pigs" !ù $%-'})
        # Do: subscribe Raoul
        group_pigs.message_subscribe([self.partner_raoul_id])
        # Test: group followers = Raoul + uid
        self.assertEqual(set([self.partner_raoul_id, self.partner_admin_id]), set(group_pigs.message_follower_ids.ids),
                        'message_subscribe: incorrect followers after subscribe')
        # Do: Raoul message_post on Pigs
        self._init_mock_build_email()
        msg1_id = group_pigs.sudo(user_raoul.id).message_post(
                            body=_body1, subject=_subject, partner_ids=[p_b.id, p_c.id],
                            attachment_ids=[attach1.id, attach2.id], attachments=_attachments,
                            type='comment', subtype='mt_comment')
        msg = self.MailMessage.browse(msg1_id)
        msg_message_id = msg.message_id
        sent_emails = self._build_email_kwargs_list
        # Test: mail_message: subject and body not modified
        self.assertEqual(_subject, msg.subject, 'message_post: mail.message subject incorrect')
        self.assertEqual(_body1, msg.body, 'message_post: mail.message body incorrect')
        # Test: mail_message: notified_partner_ids = group followers + partner_ids - author
        self.assertEqual(set([self.partner_admin_id, p_b.id, p_c.id]), set(msg.notified_partner_ids.ids), 'message_post: mail.message notified partners incorrect')
        # Test: mail_message: attachments (4, attachment_ids + attachments)
        msg_attach_names = set([attach.name for attach in msg.attachment_ids])
        self.assertEqual(len(msg.attachment_ids.ids), 4,
                        'message_post: mail.message wrong number of attachments')
        self.assertEqual(msg_attach_names, set(['Attach1', 'Attach2', 'List1', 'List2']),
                        'message_post: mail.message attachments incorrectly added')
        self.assertTrue(set([attach1.id, attach2.id]).issubset(set(msg.attachment_ids.ids)),
                        'message_post: mail.message attachments duplicated')
        for attach in msg.attachment_ids:
            self.assertEqual(attach.res_model, 'mail.group',
                            'message_post: mail.message attachments were not linked to the document')
            self.assertEqual(attach.res_id, group_pigs.id,
                            'message_post: mail.message attachments were not linked to the document')
            if 'List' in attach.name:
                self.assertIn((attach.name, attach.datas.decode('base64')), _attachments,
                                'message_post: mail.message attachment name / data incorrect')
                dl_attach = self.MailMessage.sudo(user_raoul.id).download_attachment(msg.id,attachment_id=attach.id)
                self.assertIn((dl_attach['filename'], dl_attach['base64'].decode('base64')), _attachments,
                                'message_post: mail.message download_attachment is incorrect')
        # Test: followers: same as before (author was already subscribed)

        self.assertEqual(set([self.partner_raoul_id, self.partner_admin_id]), set(group_pigs.message_follower_ids.ids),
                        'message_post: wrong followers after posting')
        # Test: mail_mail: notifications have been deleted
        self.assertFalse(self.MailMail.search([('mail_message_id', '=', msg1_id)]),
                        'message_post: mail.mail notifications should have been auto-deleted!')
        # Test: notifications emails: to a and b, c is email only, r is author
        test_emailto = ['Administrator <a@a>', 'Bert Tartopoils <b@b>']
        # test_emailto = ['"Followers of -Pigs-" <a@a>', '"Followers of -Pigs-" <b@b>']
        self.assertEqual(len(sent_emails), 2,
                        'message_post: notification emails wrong number of send emails')
        self.assertEqual(set([m['email_to'][0] for m in sent_emails]), set(test_emailto),
                        'message_post: notification emails wrong recipients (email_to)')
        for sent_email in sent_emails:
            self.assertEqual(sent_email['email_from'], 'Raoul Grosbedon <raoul@schlouby.fr>',
                            'message_post: notification email wrong email_from: should use alias of sender')
            self.assertEqual(len(sent_email['email_to']), 1,
                            'message_post: notification email sent to more than one email address instead of a precise partner')
            self.assertIn(sent_email['email_to'][0], test_emailto,
                            'message_post: notification email email_to incorrect')
            self.assertEqual(sent_email['reply_to'], u'"YourCompany \\"Pigs\\" !ù $%-" <group+pigs@schlouby.fr>',
                            'message_post: notification email reply_to incorrect')
            self.assertEqual(_subject, sent_email['subject'],
                            'message_post: notification email subject incorrect')
            self.assertIn(_body1, sent_email['body'],
                            'message_post: notification email body incorrect')
            self.assertIn('Pigs rules', sent_email['body_alternative'],
                            'message_post: notification email body alternative should contain the body')
            self.assertNotIn('<p>', sent_email['body_alternative'],
                            'message_post: notification email body alternative still contains html')
            self.assertFalse(sent_email['references'],'message_post: references should be False when sending a message that is not a reply')
        # Test: notification linked to this message = group followers = notified_partner_ids
        notifications = self.MailNotification.search([('message_id', '=', msg1_id)])
        notif_pids = set([notif.partner_id.id for notif in notifications])
        self.assertEqual(set(notif_pids), set([self.partner_admin_id, p_b.id, p_c.id]),
                        'message_post: mail.message created mail.notification incorrect')
        # Data: Pigs name back to normal
        self.group_pigs.write({'name': 'Pigs'})

        # --------------------------------------------------
        # CASE2: reply + parent_id + parent notification
        # --------------------------------------------------

        # Data: remove alias_domain to see emails with alias
        self.env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')]).unlink()
        # Do: Raoul message_post on Pigs
        self._init_mock_build_email()
        msg2_id = self.group_pigs.with_context({'mail_post_autofollow': True}).sudo(user_raoul.id).message_post(
                        body=_body2, type='email', subtype='mt_comment',
                        partner_ids=[p_d.id], parent_id=msg1_id, attachment_ids=[attach3.id])
        msg = self.MailMessage.browse(msg2_id)
        sent_emails = self._build_email_kwargs_list
        # Test: mail_message: subject is False, body, parent_id is msg_id
        self.assertEqual(msg.subject, False, 'message_post: mail.message subject incorrect')
        self.assertEqual(msg.body, html_sanitize(_body2), 'message_post: mail.message body incorrect')
        self.assertEqual(msg.parent_id.id, msg1_id, 'message_post: mail.message parent_id incorrect')
        # Test: mail_message: notified_partner_ids = group followers
        self.assertEqual(set([self.partner_admin_id, p_d.id]), set(msg.notified_partner_ids.ids), 'message_post: mail.message partners incorrect')
        # Test: mail_message: notifications linked to this message = group followers = notified_partner_ids
        notifications = self.MailNotification.search([('message_id', '=', msg2_id)])
        notif_pids = set([notif.partner_id.id for notif in notifications])
        self.assertEqual(set([self.partner_admin_id, p_d.id]), set(notif_pids), 'message_post: mail.message notification partners incorrect')
        # Test: mail_mail: notifications deleted
        self.assertFalse(self.MailMail.search([('mail_message_id', '=', msg2_id)]), 'mail.mail notifications should have been auto-deleted!')
        # Test: emails send by server (to a, b, c, d)
        test_emailto = [u'Administrator <a@a>', u'Bert Tartopoils <b@b>', u'Carine Poilvache <c@c>', u'D\xe9d\xe9 Grosbedon <d@d>']
        # test_emailto = [u'"Followers of Pigs" <a@a>', u'"Followers of Pigs" <b@b>', u'"Followers of Pigs" <c@c>', u'"Followers of Pigs" <d@d>']
        # self.assertEqual(len(sent_emails), 3, 'sent_email number of sent emails incorrect')
        for sent_email in sent_emails:
            self.assertEqual(sent_email['email_from'], 'Raoul Grosbedon <r@r>',
                            'message_post: notification email wrong email_from: should use email of sender when no alias domain set')
            self.assertEqual(len(sent_email['email_to']), 1,
                            'message_post: notification email sent to more than one email address instead of a precise partner')
            self.assertIn(sent_email['email_to'][0], test_emailto,
                            'message_post: notification email email_to incorrect')
            self.assertEqual(email_split(sent_email['reply_to']), ['r@r'],  # was '"Followers of Pigs" <r@r>', but makes no sense
                            'message_post: notification email reply_to incorrect: should have raoul email')
            self.assertEqual(_mail_subject, sent_email['subject'],
                            'message_post: notification email subject incorrect')
            self.assertIn(html_sanitize(_body2), sent_email['body'],
                            'message_post: notification email does not contain the body')
            self.assertIn('Pigs rocks', sent_email['body_alternative'],
                            'message_post: notification email body alternative should contain the body')
            self.assertNotIn('<p>', sent_email['body_alternative'],
                            'message_post: notification email body alternative still contains html')
            self.assertIn(msg_message_id, sent_email['references'],
                            'message_post: notification email references lacks parent message message_id')
        # Test: attachments + download
        for attach in msg.attachment_ids:
            self.assertEqual(attach.res_model, 'mail.group',
                            'message_post: mail.message attachment res_model incorrect')
            self.assertEqual(attach.res_id, self.group_pigs.id,
                            'message_post: mail.message attachment res_id incorrect')

        # Test: Dédé has been notified -> should also have been notified of the parent message
        msg = self.MailMessage.browse(msg1_id)
        self.assertEqual(set([self.partner_admin_id, p_b.id, p_c.id, p_d.id]), set(msg.notified_partner_ids.ids), 'message_post: mail.message parent notification not created')

         # Do: reply to last message
        msg3_id = self.group_pigs.sudo(user_raoul.id).message_post(body='Test', parent_id=msg2_id)
        msg = self.MailMessage.browse(msg3_id)
        # Test: check that its parent will be the first message
        self.assertEqual(msg.parent_id.id, msg1_id, 'message_post did not flatten the thread structure')

    def test_25_message_compose_wizard(self):
        """ Tests designed for the mail.compose.message wizard. """
        user_raoul, group_pigs = self.user_raoul, self.group_pigs
        MailComposeMessage = self.env['mail.compose.message']

        # --------------------------------------------------
        # Data creation
        # --------------------------------------------------

        # 0 - Update existing users-partners
        self.user_admin.write({'email': 'a@a'})
        self.user_raoul.write({'email': 'r@r'})
        # 1 - Bert Tartopoils, with email, should receive emails for comments and emails
        p_b = self.ResPartner.create({'name': 'Bert Tartopoils', 'email': 'b@b'})
        # 2 - Carine Poilvache, with email, should receive emails for emails
        p_c = self.ResPartner.create({'name': 'Carine Poilvache', 'email': 'c@c', 'notify_email': 'always'})
        # 3 - Dédé Grosbedon, without email, to test email verification; should receive emails for every message
        p_d = self.ResPartner.create({'name': 'Dédé Grosbedon', 'email': 'd@d', 'notify_email': 'always'})
        # 4 - Create a Bird mail.group, that will be used to test mass mailing
        group_bird = self.MailGroup.with_context({'mail_create_nolog': True}).create({
                'name': 'Bird',
                'description': 'Bird resistance'})
        # 5 - Mail data
        _subject = 'Pigs'
        _body = 'Pigs <b>rule</b>'
        _reply_subject = 'Re: %s' % _subject
        _attachments = [
            {'name': 'First', 'datas_fname': 'first.txt', 'datas': 'My first attachment'.encode('base64')},
            {'name': 'Second', 'datas_fname': 'second.txt', 'datas': 'My second attachment'.encode('base64')}
            ]
        _attachments_test = [('first.txt', 'My first attachment'), ('second.txt', 'My second attachment')]
        # 6 - Subscribe Bert to Pigs
        group_pigs.message_subscribe([p_b.id])


        # --------------------------------------------------
        # CASE1: wizard + partners + context keys
        # --------------------------------------------------

        # Do: Raoul wizard-composes on Pigs with auto-follow for partners, not for author
        compose = MailComposeMessage.with_context({
                'default_composition_mode': 'comment',
                'default_model': 'mail.group',
                'default_res_id': self.group_pigs.id,
            }).sudo(user_raoul.id).create({'subject': _subject,
                'body': _body,
                'partner_ids': [(4, p_c.id), (4, p_d.id)]})
        # Test: mail.compose.message: composition_mode, model, res_id
        self.assertEqual(compose.composition_mode,  'comment', 'compose wizard: mail.compose.message incorrect composition_mode')
        self.assertEqual(compose.model,  'mail.group', 'compose wizard: mail.compose.message incorrect model')
        self.assertEqual(compose.res_id, self.group_pigs.id, 'compose wizard: mail.compose.message incorrect res_id')
        # Do: Post the comment

        compose.with_context({'mail_post_autofollow': True, 'mail_create_nosubscribe': True}).sudo(user_raoul.id).send_mail()
        message = group_pigs.message_ids[0]
        # Test: mail_mail: notifications have been deleted
        self.assertFalse(self.MailMail.search([('mail_message_id', '=', message.id)]),'message_send: mail.mail message should have been auto-deleted!')
        # Test: mail.group: followers (c and d added by auto follow key; raoul not added by nosubscribe key)
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([self.partner_admin_id, p_b.id, p_c.id, p_d.id]),
                        'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')
        # Test: mail.message: subject, body inside p
        self.assertEqual(message.subject, _subject, 'compose wizard: mail.message incorrect subject')
        self.assertEqual(message.body, '<p>%s</p>' % _body, 'compose wizard: mail.message incorrect body')
        # Test: mail.message: notified_partner_ids = admin + bert (followers) + c + d (recipients)
        self.assertEqual(set(message.notified_partner_ids.ids), set([self.partner_admin_id, p_b.id, p_c.id, p_d.id]),
                        'compose wizard: mail.message notified_partner_ids incorrect')

        # --------------------------------------------------
        # CASE2: reply + attachments
        # --------------------------------------------------

        # Do: Reply with attachments
        compose = MailComposeMessage.with_context({
                'default_composition_mode': 'comment',
                'default_res_id': self.group_pigs.id,
                'default_parent_id': message.id
            }).sudo(user_raoul.id).create({'attachment_ids': [(0, 0, _attachments[0]), (0, 0, _attachments[1])]})
        # Test: mail.compose.message: model, res_id, parent_id
        self.assertEqual(compose.model, 'mail.group', 'compose wizard: mail.compose.message incorrect model')
        self.assertEqual(compose.res_id, self.group_pigs.id, 'compose wizard: mail.compose.message incorrect res_id')
        self.assertEqual(compose.parent_id.id, message.id, 'compose wizard: mail.compose.message incorrect parent_id')
        # Test: mail.compose.message: subject as Re:.., body, parent_id
        self.assertEqual(compose.subject, _reply_subject, 'compose wizard: mail.compose.message incorrect subject')
        self.assertFalse(compose.body, 'compose wizard: mail.compose.message body should not contain parent message body')
        self.assertEqual(compose.parent_id and compose.parent_id.id, message.id, 'compose wizard: mail.compose.message parent_id incorrect')
        # Test: mail.compose.message: attachments
        for attach in compose.attachment_ids:
            self.assertIn((attach.datas_fname, attach.datas.decode('base64')), _attachments_test,
                            'compose wizard: mail.message attachment name / data incorrect')

        # --------------------------------------------------
        # CASE3: mass_mail on Pigs and Bird
        # --------------------------------------------------

        # Do: Compose in mass_mail_mode on pigs and bird
        compose = MailComposeMessage.with_context({
                'default_composition_mode': 'mass_mail',
                'default_model': 'mail.group',
                'default_res_id': False,
                'active_ids': [self.group_pigs.id, group_bird.id]
            }).sudo(user_raoul.id).create({
                'subject': _subject,
                'body': '${object.description}',
                'partner_ids': [(4, p_c.id), (4, p_d.id)]})
        # Do: Post the comment, get created message for each group
        compose.with_context({
                        'default_res_id': -1,
                        'active_ids': [group_pigs.id, group_bird.id]
                    }).sudo(user_raoul.id).send_mail()
        # check mail_mail
        mails = self.MailMail.search([('subject', '=', _subject)])
        for mail in mails:
            self.assertEqual(set(mail.recipient_ids.ids), set([p_c.id, p_d.id]),
                        'compose wizard: mail_mail mass mailing: mail.mail in mass mail incorrect recipients')
        # check logged messages
        message1 = group_pigs.message_ids[0]
        message2 = group_bird.message_ids[0]
        # Test: Pigs and Bird did receive their message
        messages = self.MailMessage.search([], limit=2)
        mail = self.MailMail.search([('mail_message_id', '=', message2.id)], limit=1)
        self.assertTrue(mail, 'message_send: mail.mail message should have in processing mail queue')
        #check mass mail state...
        mails = self.MailMail.search([('state', '=', 'exception')])
        self.assertNotIn(mail.id, mails.ids, 'compose wizard: Mail sending Failed!!')
        self.assertIn(message1.id, messages.ids, 'compose wizard: Pigs did not receive its mass mailing message')
        self.assertIn(message2.id, messages.ids, 'compose wizard: Bird did not receive its mass mailing message')
        # Test: mail.message: subject, body, subtype, notified partners (nobody + specific recipients)
        self.assertEqual(message1.subject, _subject,
                        'compose wizard: message_post: mail.message in mass mail subject incorrect')
        self.assertEqual(message1.body, '<p>%s</p>' % group_pigs.description,
                        'compose wizard: message_post: mail.message in mass mail body incorrect')
        # self.assertEqual(set([p.id for p in message1.notified_partner_ids]), set([p_c, p_d]),
        #                 'compose wizard: message_post: mail.message in mass mail incorrect notified partners')
        self.assertEqual(message2.subject, _subject,
                        'compose wizard: message_post: mail.message in mass mail subject incorrect')
        self.assertEqual(message2.body, '<p>%s</p>' % group_bird.description,
                        'compose wizard: message_post: mail.message in mass mail body incorrect')
        # self.assertEqual(set([p.id for p in message2.notified_partner_ids]), set([p_c, p_d]),
        #                 'compose wizard: message_post: mail.message in mass mail incorrect notified partners')

        # Test: mail.group followers: author not added as follower in mass mail mode
        self.assertEqual(set(group_pigs.message_follower_ids.ids), set([self.partner_admin_id, p_b.id, p_c.id, p_d.id]),
                        'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')
        self.assertEqual(set(group_bird.message_follower_ids.ids), set([self.partner_admin_id]),
                        'compose wizard: mail_post_autofollow and mail_create_nosubscribe context keys not correctly taken into account')

        # Do: Compose in mass_mail, coming from list_view, we have an active_domain that should be supported
        compose = MailComposeMessage.with_context({
                'default_composition_mode': 'mass_mail',
                'default_model': 'mail.group',
                'default_res_id': False,
                'active_ids': [self.group_pigs.id],
                'active_domain': [('name', 'in', ['Pigs', 'Bird'])],
            }).sudo(user_raoul.id).create(
            {
                'subject': _subject,
                'body': '${object.description}',
                'partner_ids': [(4, p_c.id), (4, p_d.id)],
            })
        # Do: Post the comment, get created message for each group
        compose.with_context({
                'default_res_id': -1,
                'active_ids': [self.group_pigs.id, group_bird.id]
            }).sudo(user_raoul.id).send_mail()
        message1 = group_pigs.message_ids[0]
        message2 = group_bird.message_ids[0]

        # Test: Pigs and Bird did receive their message
        messages = self.MailMessage.search([], limit=2)
        self.assertIn(message1.id, messages.ids, 'compose wizard: Pigs did not receive its mass mailing message')
        self.assertIn(message2.id, messages.ids, 'compose wizard: Bird did not receive its mass mailing message')

    def test_30_needaction(self):
        """ Tests for mail.message needaction. """
        user_admin, user_raoul, group_pigs = self.user_admin, self.user_raoul, self.group_pigs
        na_admin_base = self.MailMessage._needaction_count(domain=[])
        na_demo_base = self.MailMessage.sudo(user_raoul.id)._needaction_count(domain=[])
        # Test: number of unread notification = needaction on mail.message
        no_of_notify = self.MailNotification.search_count([
            ('partner_id', '=', user_admin.partner_id.id),
            ('is_read', '=', False)])
        na_count = self.MailMessage._needaction_count(domain=[])
        self.assertEqual(no_of_notify, na_count, 'unread notifications count does not match needaction count')
        # Do: post 2 message on group_pigs as admin, 3 messages as demo user
        for dummy in range(2):
            group_pigs.message_post(body='My Body', subtype='mt_comment')
        raoul_pigs = group_pigs.sudo(user_raoul)
        for dummy in range(3):
            raoul_pigs.message_post(body='My Demo Body', subtype='mt_comment')
        # Test: admin has 3 new notifications (from demo), and 3 new needaction
        no_of_notify = self.MailNotification.search_count([
            ('partner_id', '=', user_admin.partner_id.id),
            ('is_read', '=', False)])
        self.assertEqual(no_of_notify, na_admin_base + 3, 'Admin should have 3 new unread notifications')
        na_admin = self.MailMessage._needaction_count(domain=[])
        na_admin_group = self.MailMessage._needaction_count(domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)])
        self.assertEqual(na_admin, na_admin_base + 3, 'Admin should have 3 new needaction')
        self.assertEqual(na_admin_group, 3, 'Admin should have 3 needaction related to Pigs')
        # Test: demo has 0 new notifications (not a follower, not receiving its own messages), and 0 new needaction
        no_of_notify = self.MailNotification.search_count([
            ('partner_id', '=', user_raoul.partner_id.id),
            ('is_read', '=', False)])
        self.assertEqual(no_of_notify, na_demo_base + 0, 'Demo should have 0 new unread notifications')
        na_demo = self.MailMessage.sudo(user_raoul.id)._needaction_count(domain=[])
        na_demo_group = self.MailMessage.sudo(user_raoul.id)._needaction_count(domain=[('model', '=', 'mail.group'), ('res_id', '=', self.group_pigs.id)])
        self.assertEqual(na_demo, na_demo_base + 0, 'Demo should have 0 new needaction')
        self.assertEqual(na_demo_group, 0, 'Demo should have 0 needaction related to Pigs')

    def test_40_track_field(self):
        """ Testing auto tracking of fields. """
        def _strip_string_spaces(body):
            return body.replace(' ', '').replace('\n', '')
        # Data: subscribe Raoul to Pigs, because he will change the public attribute and may loose access to the record
        group_pigs, user_raoul = self.group_pigs, self.user_raoul
        group_pigs.message_subscribe_users(user_ids=[user_raoul.id])
        # Data: res.users.group, to test group_public_id automatic logging
        group_system_id = self.IrModelData.xmlid_to_res_id('base.group_system') or False
        # Data: custom subtypes
        mt_private = self.MailMessageSubtype.create({'name': 'private', 'description': 'Private public'})
        self.IrModelData.create({'name': 'mt_private', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_private.id})
        mt_name_supername = self.MailMessageSubtype.create({'name': 'name_supername', 'description': 'Supername name'})
        self.IrModelData.create({'name': 'mt_name_supername', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_name_supername.id})
        mt_group_public_set = self.MailMessageSubtype.create({'name': 'group_public_set', 'description': 'Group set'})
        self.IrModelData.create({'name': 'mt_group_public_set', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public_set.id})
        mt_group_public = self.MailMessageSubtype.create({'name': 'group_public', 'description': 'Group changed'})
        self.IrModelData.create({'name': 'mt_group_public', 'model': 'mail.message.subtype', 'module': 'mail', 'res_id': mt_group_public.id})
        # Data: alter mail_group model for testing purposes (test on classic, selection and many2one fields)
        cls = type(self.MailGroup)
        self.assertNotIn('_track', cls.__dict__)
        cls._track = {
            'public': {
                'mail.mt_private': lambda self, cr, uid, obj, ctx=None: obj.public == 'private',
            },
            'name': {
                'mail.mt_name_supername': lambda self, cr, uid, obj, ctx=None: obj.name == 'supername',
            },
            'group_public_id': {
                'mail.mt_group_public_set': lambda self, cr, uid, obj, ctx=None: obj.group_public_id,
                'mail.mt_group_public': lambda self, cr, uid, obj, ctx=None: True,
            },
        }
        visibility = {'public': 'onchange', 'name': 'always', 'group_public_id': 'onchange'}
        for key in visibility:
            self.assertFalse(hasattr(getattr(cls, key), 'track_visibility'))
            getattr(cls, key).track_visibility = visibility[key]

        @self.addCleanup
        def cleanup():
            delattr(cls, '_track')
            for key in visibility:
                del getattr(cls, key).track_visibility

        # Test: change name -> always tracked, not related to a subtype
        self.group_pigs.sudo(user_raoul.id).write({'public': 'public'})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 1, 'tracked: a message should have been produced')
        # Test: first produced message: no subtype, name change tracked
        last_msg = self.group_pigs.message_ids[-1]
        self.assertFalse(last_msg.subtype_id, 'tracked: message should not have been linked to a subtype')
        self.assertIn(u"Selectedgroupofusers\u2192Everyone", _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        self.assertIn('Pigs', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')
        # Test: change name as supername, public as private -> 2 subtypes
        self.group_pigs.sudo(user_raoul.id).write({'name': 'supername', 'public': 'private'})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 3, 'tracked: two messages should have been produced')
        # Test: first produced message: mt_name_supername
        last_msg = self.group_pigs.message_ids[-2]
        self.assertEqual(last_msg.subtype_id.id, mt_private.id, 'tracked: message should be linked to mt_private subtype')
        self.assertIn('Private public', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Pigs\u2192supername', _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        # Test: second produced message: mt_name_supername
        last_msg = self.group_pigs.message_ids[-3]
        self.assertEqual(last_msg.subtype_id.id, mt_name_supername.id, 'tracked: message should be linked to mt_name_supername subtype')
        self.assertIn('Supername name', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u"Everyone\u2192Invitedpeopleonly", _strip_string_spaces(last_msg.body), 'tracked: message body incorrect')
        self.assertIn(u'Pigs\u2192supername', _strip_string_spaces(last_msg.body), 'tracked feature: message body does not hold always tracked field')
        # Test: change public as public, group_public_id -> 2 subtypes, name always tracked
        self.group_pigs.write({'public': 'public', 'group_public_id': group_system_id})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 5, 'tracked: one message should have been produced')
        # Test: first produced message: mt_group_public_set_id, with name always tracked, public tracked on change
        last_msg = self.group_pigs.message_ids[-4]
        self.assertEqual(last_msg.subtype_id.id, mt_group_public_set.id, 'tracked: message should be linked to mt_group_public_set_id')
        self.assertIn('Group set', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u"Invitedpeopleonly\u2192Everyone", _strip_string_spaces(last_msg.body), 'tracked: message body does not hold changed tracked field')
        self.assertIn(u'HumanResources/Employee\u2192Administration/Settings', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')
        # Test: second produced message: mt_group_public_id, with name always tracked, public tracked on change
        last_msg = self.group_pigs.message_ids[-5]
        self.assertEqual(last_msg.subtype_id.id, mt_group_public.id, 'tracked: message should be linked to mt_group_public_id')
        self.assertIn('Group changed', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u"Invitedpeopleonly\u2192Everyone", _strip_string_spaces(last_msg.body), 'tracked: message body does not hold changed tracked field')
        self.assertIn(u'HumanResources/Employee\u2192Administration/Settings', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')
        # Test: change group_public_id to False -> 1 subtype, name always tracked
        self.group_pigs.sudo(user_raoul.id).write({'group_public_id': False})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 6, 'tracked: one message should have been produced')
        # Test: first produced message: mt_group_public_set_id, with name always tracked, public tracked on change
        last_msg = self.group_pigs.message_ids[-6]
        self.assertEqual(last_msg.subtype_id.id, mt_group_public.id, 'tracked: message should be linked to mt_group_public_id')
        self.assertIn('Group changed', last_msg.body, 'tracked: message body does not hold the subtype description')
        self.assertIn(u'Administration/Settings\u2192', _strip_string_spaces(last_msg.body), 'tracked: message body does not hold always tracked field')
        # Test: change not tracked field, no tracking message
        self.group_pigs.sudo(user_raoul.id).write({'description': 'Dummy'})
        self.assertEqual(len(self.group_pigs.message_ids.ids), 6, 'tracked: No message should have been produced')
