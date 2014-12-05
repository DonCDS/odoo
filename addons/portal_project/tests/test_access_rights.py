# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.addons.project.tests.test_project_base import TestProjectBase
from openerp.exceptions import AccessError
from openerp.exceptions import except_orm
from openerp.tools import mute_logger


class TestPortalProjectBase(TestProjectBase):

    def setUp(self):
        super(TestPortalProjectBase, self).setUp()
        # Find Portal group
        self.group_portal_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_portal') or False
        # Find Public group
        self.group_public_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_public') or False
        # # Test users to use through the various tests
        self.user_portal = self.ResUsers.create({
            'name': 'Chell Portal',
            'login': 'chell',
            'alias_name': 'chell',
            'groups_id': [(6, 0, [self.group_portal_id])]
        })
        self.user_public = self.ResUsers.create({
            'name': 'Donovan Public',
            'login': 'donovan',
            'alias_name': 'donovan',
            'groups_id': [(6, 0, [self.group_public_id])]
        })
        self.user_manager = self.ResUsers.create({
            'name': 'Eustache Manager',
            'login': 'eustache',
            'alias_name': 'eustache',
            'groups_id': [(6, 0, [self.group_project_manager_id])]
        })
        # Test 'Pigs' project
        self.project_pigs = self.Project.with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs', 'privacy_visibility': 'public'})
        # Various test tasks
        self.task_1 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Test1', 'user_id': False, 'project_id': self.project_pigs.id})
        self.task_2 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Test2', 'user_id': False, 'project_id': self.project_pigs.id})
        self.task_3 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Test3', 'user_id': False, 'project_id': self.project_pigs.id})
        self.task_4 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Test4', 'user_id': self.user_projectuser.id, 'project_id': self.project_pigs.id})
        self.task_5 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Test5', 'user_id': self.user_portal.id, 'project_id': self.project_pigs.id})
        self.task_6 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Test6', 'user_id': self.user_public.id, 'project_id': self.project_pigs.id})

class TestPortalProject(TestPortalProjectBase):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_project_access_rights(self):
        """ Test basic project access rights, for project and portal_project """
        pigs = self.project_pigs

        # ----------------------------------------
        # CASE1: public project
        # ----------------------------------------

        # Do: Alfred reads project -> ok (employee ok public)
        pigs.sudo(self.user_projectuser.id).read(['state'])
        # Test: all project tasks visible
        tasks = self.ProjectTask.sudo(self.user_projectuser.id).search([('project_id', '=', pigs.id)])
        test_task_ids = set([self.task_1.id, self.task_2.id, self.task_3.id, self.task_4.id, self.task_5.id, self.task_6.id])
        self.assertEqual(set(tasks.ids), test_task_ids, 'access rights: project user cannot see all tasks of a public project')
        # Test: all project tasks readable
        tasks.sudo(self.user_projectuser.id).read(['name'])
        # Test: all project tasks writable
        tasks.sudo(self.user_projectuser.id).write({'description': 'TestDescription'})
        # Need to check assertRaises
        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_none.id).read, ['state'])
        # Test: no project task visible
        self.assertRaises(AccessError, self.ProjectTask.sudo(self.user_none.id).search, [('project_id', '=', pigs.id)])
        # Test: no project task readable
        self.assertRaises(AccessError, tasks.sudo(self.user_none.id).read, ['name'])
        # Test: no project task writable
        self.assertRaises(AccessError, tasks.sudo(self.user_none.id).write, {'description': 'TestDescription'})
        # Do: Chell reads project -> ok (portal ok public)
        pigs.sudo(self.user_portal.id).read(['state'])
        # Test: all project tasks visible
        tasks = self.ProjectTask.sudo(self.user_portal.id).search([('project_id', '=', pigs.id)])
        self.assertEqual(set(tasks.ids), test_task_ids,
                        'access rights: project user cannot see all tasks of a public project')
        # Test: all project tasks readable
        tasks.read(['name'])
        # Test: no project task writable
        self.assertRaises(AccessError, tasks.sudo(self.user_portal.id).write, {'description': 'TestDescription'})
        # Do: Donovan reads project -> ok (public)
        pigs.sudo(self.user_public.id).read(['state'])
        # Test: all project tasks visible
        tasks = self.ProjectTask.sudo(self.user_public.id).search([('project_id', '=', pigs.id)])
        self.assertEqual(set(tasks.ids), test_task_ids,
                        'access rights: public user cannot see all tasks of a public project')
        # Test: all project tasks readable
        tasks.sudo(self.user_public.id).read(['name'])
        # Test: no project task writable
        self.assertRaises(AccessError, tasks.sudo(self.user_public.id).write, {'description': 'TestDescription'})

        # ----------------------------------------
        # CASE2: portal project
        # ----------------------------------------

        pigs.write({'privacy_visibility': 'portal'})
        # Do: Alfred reads project -> ok (employee ok public)
        pigs.sudo(self.user_projectuser.id).read(['state'])
        # Test: all project tasks visible
        tasks = self.ProjectTask.sudo(self.user_projectuser.id).search([('project_id', '=', pigs.id)])
        self.assertEqual(set(tasks.ids), test_task_ids,
                        'access rights: project user cannot see all tasks of a portal project')
        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_none.id).read, ['state'])
        # Test: no project task searchable
        self.assertRaises(AccessError, self.ProjectTask.sudo(self.user_none.id).search, [('project_id', '=', pigs.id)])

        # Data: task follower
        pigs.sudo(self.user_manager.id).message_subscribe_users(user_ids=[self.user_portal.id])
        self.task_1.sudo(self.user_projectuser.id).message_subscribe_users(user_ids=[self.user_portal.id])
        self.task_3.sudo(self.user_projectuser.id).message_subscribe_users(user_ids=[self.user_portal.id])
        # Do: Chell reads project -> ok (portal ok public)
        pigs.sudo(self.user_portal.id).read(['state'])
        # Do: Donovan reads project -> ko (public ko portal)
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.)
        self.assertRaises(except_orm, pigs.sudo(self.user_public.id).read, ['state'])
        # Test: no project task visible
        tasks = self.ProjectTask.sudo(self.user_public.id).search([('project_id', '=', pigs.id)])
        self.assertFalse(tasks, 'access rights: public user should not see tasks of a portal project')
        # Data: task follower cleaning
        self.task_1.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_portal.id])
        self.task_3.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_portal.id])

        # ----------------------------------------
        # CASE3: employee project
        # ----------------------------------------

        pigs.write({'privacy_visibility': 'employees'})
        # Do: Alfred reads project -> ok (employee ok employee)
        pigs.sudo(self.user_projectuser.id).read(['state'])
        # Test: all project tasks visible
        tasks = self.ProjectTask.sudo(self.user_projectuser.id).search([('project_id', '=', pigs.id)])
        test_task_ids = set([self.task_1.id, self.task_2.id, self.task_3.id, self.task_4.id, self.task_5.id, self.task_6.id])
        self.assertEqual(set(tasks.ids), test_task_ids,
                        'access rights: project user cannot see all tasks of an employees project')
        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_none.id).read, ['state'])
        # Do: Chell reads project -> ko (portal ko employee)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_portal.id).read, ['state'])
        # Test: no project task visible + assigned
        tasks = self.ProjectTask.sudo(self.user_portal.id).search([('project_id', '=', pigs.id)])
        self.assertFalse(tasks.ids, 'access rights: portal user should not see tasks of an employees project, even if assigned')
        # Do: Donovan reads project -> ko (public ko employee)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_public.id).read, ['state'])
        # Test: no project task visible
        tasks = self.ProjectTask.sudo(self.user_public.id).search([('project_id', '=', pigs.id)])
        self.assertFalse(tasks.ids, 'access rights: public user should not see tasks of an employees project')

        # Do: project user is employee and can create a task
        tmp_task = self.ProjectTask.sudo(self.user_projectuser.id).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task',
            'project_id': pigs.id})
        tmp_task.sudo(self.user_projectuser.id).unlink()

        # ----------------------------------------
        # CASE4: followers project
        # ----------------------------------------

        pigs.write({'privacy_visibility': 'followers'})
        # Do: Alfred reads project -> ko (employee ko followers)
        # TODO Change the except_orm to Warning
        self.assertRaises(AccessError, pigs.sudo(self.user_projectuser.id).read, ['state'])
        # Test: no project task visible
        tasks = self.ProjectTask.sudo(self.user_projectuser.id).search([('project_id', '=', pigs.id)])
        self.assertEqual(set(tasks.ids), set([self.task_4.id]), 
                        'access rights: employee user should not see tasks of a not-followed followers project, only assigned')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_none.id).read, ['state'])

        # Do: Chell reads project -> ko (portal ko employee)
        pigs.sudo(self.user_portal.id).message_unsubscribe_users(user_ids=[self.user_portal.id])
        self.assertRaises(except_orm, pigs.sudo(self.user_portal.id).read, ['state'])
        # Test: no project task visible
        tasks = self.ProjectTask.sudo(self.user_portal.id).search([('project_id', '=', pigs.id)])
        self.assertEqual(set(tasks.ids), set([self.task_5.id]), 
                        'access rights: portal user should not see tasks of a not-followed followers project, only assigned')
        # Do: Donovan reads project -> ko (public ko employee)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_public.id).read, ['state'])
        # Test: no project task visible
        tasks = self.ProjectTask.sudo(self.user_public.id).search([('project_id', '=', pigs.id)])
        self.assertFalse(tasks, 'access rights: public user should not see tasks of a followers project')
        # Data: subscribe Alfred, Chell and Donovan as follower
        pigs.message_subscribe_users(user_ids=[self.user_projectuser.id, self.user_portal.id, self.user_public.id])
        self.task_1.sudo(self.user_manager.id).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])
        self.task_3.sudo(self.user_manager.id).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])
        # Do: Alfred reads project -> ok (follower ok followers)
        pigs.sudo(self.user_projectuser.id).read(['state'])
        # Do: Chell reads project -> ok (follower ok follower)
        pigs.sudo(self.user_portal.id).read(['state'])
        # Do: Donovan reads project -> ko (public ko follower even if follower)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_public.id).read, ['state'])
        # Do: project user is follower of the project and can create a task
        self.ProjectTask.sudo(self.user_projectuser.id).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task', 'project_id': pigs.id
        })
        # not follower user should not be able to create a task
        pigs.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_projectuser.id])
        self.assertRaises(except_orm, self.ProjectTask.sudo(self.user_projectuser.id).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})

        # Do: project user can create a task without project
        self.assertRaises(except_orm, self.ProjectTask.sudo(self.user_projectuser.id).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})

