# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
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

class TestProjectBase(TestMail):

    def setUp(self):
        super(TestProjectBase, self).setUp()
        # Usefull models
        self.Project = self.env['project.project']
        self.ProjectTask = self.env['project.task']
        self.IrModelData = self.env['ir.model.data']
        # Find Project User group
        self.group_project_user_id = self.IrModelData.xmlid_to_res_id('project.group_project_user') or False
        # Find Project Manager group
        self.group_project_manager_id = self.IrModelData.xmlid_to_res_id('project.group_project_manager') or False
        # Test partners to use through the various tests
        self.project_partner = self.ResPartner.create({
            'name': 'Gertrude AgrolaitPartner',
            'email': 'gertrude.partner@agrolait.com'})
        self.email_partner = self.ResPartner.create({
            'name': 'Patrick Ratatouille',
            'email': 'patrick.ratatouille@agrolait.com'})
        # Test users to use through the various tests
        self.user_projectuser = self.ResUsers.create({
            'name': 'Armande ProjectUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_project_user_id])]
        })
        self.user_projectmanager = self.ResUsers.create({
            'name': 'Bastien ProjectManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.projectmanager@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_project_manager_id])]})
        self.user_none = self.ResUsers.create({
            'name': 'Charlie Avotbonkeur',
            'login': 'charlie',
            'alias_name': 'charlie',
            'email': 'charlie.noone@example.com',
            'groups_id': [(6, 0, [])]})
        # Partners
        self.partner_projectuser_id = self.user_projectuser.partner_id.id
        self.partner_projectmanager_id = self.user_projectmanager.partner_id.id
        # Test 'Pigs' project
        self.project_pigs = self.Project.with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs',
            'privacy_visibility': 'public',
            'alias_name': 'project+pigs',
            'partner_id': self.partner_raoul_id})
        # Already-existing tasks in Pigs
        self.task_1 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask',
            'user_id': self.user_projectuser.id,
            'project_id': self.project_pigs.id})
        self.task_2 = self.ProjectTask.with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs ManagerTask',
            'user_id': self.user_projectmanager.id,
            'project_id': self.project_pigs.id})
