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

from openerp.addons.portal_project.tests.test_access_rights import TestPortalProjectBase
from openerp.exceptions import AccessError
from openerp.tools import mute_logger

class TestPortalProjectBase(TestPortalProjectBase):

    def setUp(self):
        super(TestPortalProjectBase, self).setUp()
        # Useful models
        self.ProjectIssue = self.env['project.issue']
        context_nolog = {'mail_create_nolog': True}

        # Various test issues
        self.issue_1 = self.ProjectIssue.with_context(context_nolog).create({
            'name': 'Test1', 'user_id': False, 'project_id': self.project_pigs.id})
        self.issue_2 = self.ProjectIssue.with_context(context_nolog).create({
            'name': 'Test2', 'user_id': False, 'project_id': self.project_pigs.id})
        self.issue_3 = self.ProjectIssue.with_context(context_nolog).create({
            'name': 'Test3', 'user_id': False, 'project_id': self.project_pigs.id})
        self.issue_4 = self.ProjectIssue.with_context(context_nolog).create({
            'name': 'Test4', 'user_id': self.user_projectuser.id, 'project_id': self.project_pigs.id})
        self.issue_5 = self.ProjectIssue.with_context(context_nolog).create({
            'name': 'Test5', 'user_id': self.user_portal.id, 'project_id': self.project_pigs.id})
        self.issue_6 = self.ProjectIssue.with_context(context_nolog).create({
            'name': 'Test6', 'user_id': self.user_public.id, 'project_id': self.project_pigs.id})


class TestPortalIssue(TestPortalProjectBase):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_project_access_rights(self):
        """ Test basic project access rights, for project and portal_project """
        pigs_id = self.project_pigs.id

        # ----------------------------------------
        # CASE1: public project
        # ----------------------------------------

        # Do: Alfred reads project -> ok (employee ok public)
        # Test: all project issues visible
        issues = self.ProjectIssue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1.id, self.issue_2.id, self.issue_3.id, self.issue_4.id, self.issue_5.id, self.issue_6.id])
        self.assertEqual(set(issues.ids), test_issue_ids,
                         'access rights: project user cannot see all issues of a public project')
        # Test: all project issues readable
        issues.read(['name'])
        # Test: all project issues writable
        issues.sudo(self.user_projectuser.id).write({'description': 'TestDescription'})

        # Do: Bert reads project -> crash, no group
        # Test: no project issue visible
        self.assertRaises(AccessError, self.ProjectIssue.sudo(self.user_none.id).search, [('project_id', '=', pigs_id)])
        # Test: no project issue readable
        self.assertRaises(AccessError, issues.sudo(self.user_none.id).read, ['name'])
        # Test: no project issue writable
        self.assertRaises(AccessError, issues.sudo(self.user_none.id).write, {'description': 'TestDescription'})

        # Do: Chell reads project -> ok (portal ok public)
        # Test: all project issues visible
        issues = self.ProjectIssue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), test_issue_ids,
                         'access rights: project user cannot see all issues of a public project')
        # Test: all project issues readable
        issues.sudo(self.user_portal.id).read(['name'])
        # Test: no project issue writable
        self.assertRaises(AccessError, issues.sudo(self.user_portal.id).write, {'description': 'TestDescription'})

        # Do: Donovan reads project -> ok (public ok public)
        # Test: all project issues visible
        issues = self.ProjectIssue.sudo(self.user_public.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), test_issue_ids,
                         'access rights: project user cannot see all issues of a public project')

        # ----------------------------------------
        # CASE2: portal project
        # ----------------------------------------
        self.project_pigs.write({'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        # Test: all project issues visible
        issues = self.ProjectIssue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), test_issue_ids,
                         'access rights: project user cannot see all issues of a portal project')

        # Do: Bert reads project -> crash, no group
        # Test: no project issue searchable
        self.assertRaises(AccessError, self.ProjectIssue.sudo(self.user_none.id).search, [('project_id', '=', pigs_id)])

        # Data: issue follower
        self.issue_1.sudo(self.user_projectuser.id).message_subscribe_users(user_ids=[self.user_portal.id])
        self.issue_3.sudo(self.user_projectuser.id).message_subscribe_users(user_ids=[self.user_portal.id])

        # Do: Chell reads project -> ok (portal ok public)
        # Test: only followed project issues visible + assigned
        issues = self.ProjectIssue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_3.id, self.issue_5.id]),
                         'access rights: portal user should see the followed issues of a portal project')

        # Data: issue follower cleaning
        self.issue_1.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_portal.id])
        self.issue_3.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_portal.id])

        # ----------------------------------------
        # CASE3: employee project
        # ----------------------------------------
        self.project_pigs.write({'privacy_visibility': 'employees'})

        # Do: Alfred reads project -> ok (employee ok employee)
        # Test: all project issues visible
        issues = self.ProjectIssue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_2.id, self.issue_3.id,
                        self.issue_4.id, self.issue_5.id, self.issue_6.id]),
                        'access rights: project user cannot see all issues of an employees project')

        # Do: Chell reads project -> ko (portal ko employee)
        # Test: no project issue visible + assigned
        issues = self.ProjectIssue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertFalse(issues.ids, 'access rights: portal user should not see issues of an employees project, even if assigned')

        # ----------------------------------------
        # CASE4: followers project
        # ----------------------------------------
        self.project_pigs.write({'privacy_visibility': 'followers'})

        # Do: Alfred reads project -> ko (employee ko followers)
        # Test: no project issue visible
        issues = self.ProjectIssue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_4.id]),
                         'access rights: employee user should not see issues of a not-followed followers project, only assigned')

        # Do: Chell reads project -> ko (portal ko employee)
        # Test: no project issue visible
        issues = self.ProjectIssue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_5.id]),
                         'access rights: portal user should not see issues of a not-followed followers project, only assigned')

        # Data: subscribe Alfred, Chell and Donovan as follower
        self.project_pigs.message_subscribe_users(user_ids=[self.user_projectuser.id, self.user_portal.id, self.user_public.id])
        self.issue_1.sudo(self.user_manager.id).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])
        self.issue_3.sudo(self.user_manager.id).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])

        # Do: Alfred reads project -> ok (follower ok followers)
        # Test: followed + assigned issues visible
        issues = self.ProjectIssue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_3.id, self.issue_4.id]),
                         'access rights: employee user should not see followed + assigned issues of a follower project')

        # Do: Chell reads project -> ok (follower ok follower)
        # Test: followed + assigned issues visible
        issues = self.ProjectIssue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_3.id, self.issue_5.id]),
                         'access rights: employee user should not see followed + assigned issues of a follower project')
