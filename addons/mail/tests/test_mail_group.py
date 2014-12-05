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

class TestMailGroup(TestMail):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_mail_group_access_rights(self):
        """ Testing mail_group access rights and basic mail_thread features """
        user_noone, user_employee = self.user_noone, self.user_employee
        group_priv, group_jobs = self.group_priv, self.group_jobs
        # Do: Bert reads Jobs -> ok, public
        group_jobs.sudo(user_noone.id).read()
        # Do: Bert read Pigs -> ko, restricted to employees
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.So we need to change all
        # except_orm to warning in mail module.)
        with self.assertRaises(except_orm):
            self.group_pigs.sudo(user_noone.id).read()
        # Do: Raoul read Pigs -> ok, belong to employees
        self.group_pigs.sudo(user_employee.id).read()
        # Do: Bert creates a group -> ko, no access rights
        with self.assertRaises(AccessError):
            self.MailGroup.sudo(user_noone.id).create({'name': 'Test'})
        # Do: Raoul creates a restricted group -> ok
        new_group = self.MailGroup.sudo(user_employee.id).create({'name': 'Test'})
        # Do: Bert added in followers, read -> ok, in followers
        new_group.message_subscribe_users(user_ids=[user_noone.id])
        new_group.sudo(user_noone.id).read()
        # Do: Raoul reads Priv -> ko, private
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            group_priv.sudo(user_employee.id).read()
        # Do: Raoul added in follower, read -> ok, in followers
        group_priv.message_subscribe_users(user_ids=[user_employee.id])
        group_priv.sudo(user_employee.id).read()
        # Do: Raoul write on Jobs -> ok
        group_priv.sudo(user_employee.id).write({'name': 'modified'})
        # Do: Bert cannot write on Private -> ko (read but no write)
        with self.assertRaises(AccessError):
            group_priv.sudo(user_noone.id).write({'name': 're-modified'})
        # Test: Bert cannot unlink the group
        # TODO Change the except_orm to Warning
        with self.assertRaises(except_orm):
            group_priv.sudo(user_noone.id).unlink()
        #Do: Raoul unlinks the group, there are no followers and messages left
        group_priv.sudo(user_employee.id).unlink()
        no_of_fol = self.MailFollowers.search_count([('res_model', '=', 'mail.group'), ('res_id', '=', group_priv.id)])
        self.assertFalse(no_of_fol, 'unlinked document should not have any followers left')
        no_of_msg = self.MailMessage.search_count([('model', '=', 'mail.group'), ('res_id', '=', group_priv.id)])
        self.assertFalse(no_of_msg, 'unlinked document should not have any followers left')
