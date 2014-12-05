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

from openerp.tests import common

class TestMail(common.TransactionCase):

    def _init_mock_build_email(self):
        self._build_email_args_list = []
        self._build_email_kwargs_list = []

    def setUp(self):
        super(TestMail, self).setUp()
        Test = self

        def build_email(self, *args, **kwargs):
            Test._build_email_args_list.append(args)
            Test._build_email_kwargs_list.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        def send_email(self, cr, uid, message, *args, **kwargs):
            return message['Message-Id']

        self._init_mock_build_email()
        self.IrMailServer = self.env['ir.mail_server']
        self.IrMailServer._patch_method('build_email', build_email)
        self.IrMailServer._patch_method('send_email', send_email)
        # Usefull models
        self.IrModel = self.env['ir.model']
        self.IrModelData = self.env['ir.model.data']
        self.IrAttachment = self.env['ir.attachment']
        self.MailAlias = self.env['mail.alias']
        self.MailThread = self.env['mail.thread']
        self.MailGroup = self.env['mail.group']
        self.MailMail = self.env['mail.mail']
        self.MailMessage = self.env['mail.message']
        self.MailNotification = self.env['mail.notification']
        self.MailFollowers = self.env['mail.followers']
        self.MailMessageSubtype = self.env['mail.message.subtype']
        self.ResUsers =self.env['res.users'].with_context({'no_reset_password': True})
        self.ResPartner = self.env['res.partner']
        # Find Employee group
        self.group_employee_id = self.IrModelData.xmlid_to_res_id('base.group_user') or False
        self.user_admin = self.env.user
        # Partner Data
        # User Data: employee, noone
        self.user_employee = self.ResUsers.create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'alias_name': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notify_email': 'always',
            'groups_id': [(6, 0, [self.group_employee_id])]})
        self.user_noone = self.ResUsers.create({
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'alias_name': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notify_email': 'always',
            'groups_id': [(6, 0, [])]})
        self.user_admin.write({'name': 'Administrator'})
        # Test users to use through the various tests
        self.user_raoul = self.ResUsers.create({
            'name': 'Raoul Grosbedon',
            'signature': 'SignRaoul',
            'email': 'raoul@raoul.fr',
            'login': 'raoul',
            'alias_name': 'raoul',
            'groups_id': [(6, 0, [self.group_employee_id])]})
        self.user_bert = self.ResUsers.create({
            'name': 'Bert Tartignole',
            'signature': 'SignBert',
            'email': 'bert@bert.fr',
            'login': 'bert',
            'alias_name': 'bert',
            'groups_id': [(6, 0, [])]})
        self.partner_admin_id = self.user_admin.partner_id.id
        self.partner_raoul_id = self.user_raoul.partner_id.id
        self.partner_bert_id = self.user_bert.partner_id.id
        # Test 'pigs' group to use through the various tests
        self.group_pigs = self.MailGroup.with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs', 'description': 'Fans of Pigs, unite !', 'alias_name': 'group+pigs'})
        # Test mail.group: public to provide access to everyone
        self.group_jobs = self.MailGroup.create({'name': 'Jobs', 'public': 'public'})
        # Test mail.group: private to restrict access
        self.group_priv = self.MailGroup.create({'name': 'Private', 'public': 'private'})

    def tearDown(self):
        # Remove mocks
        self.IrMailServer._revert_method('build_email')
        self.IrMailServer._revert_method('send_email')
        super(TestMail, self).tearDown()
