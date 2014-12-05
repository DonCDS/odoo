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

from openerp.addons.project.tests.test_project_base import TestProjectBase
from openerp.exceptions import AccessError
from openerp.tools import mute_logger


EMAIL_TPL = """Return-Path: <whatever-2a840@postmaster.twitter.com>
X-Original-To: {email_to}
Delivered-To: {email_to}
To: {email_to}
cc: {cc}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
Message-ID: {msg_id}
Date: Tue, 29 Nov 2011 12:43:21 +0530
From: {email_from}
MIME-Version: 1.0
Subject: {subject}
Content-Type: text/plain; charset=ISO-8859-1; format=flowed

Hello,

This email should create a new entry in your module. Please check that it
effectively works.

Thanks,

--
Raoul Boitempoils
Integrator at Agrolait"""


class TestProjectFlow(TestProjectBase):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_project_process(self):
        """ Testing project management """
        user_projectuser, user_projectmanager, project_pigs = self.user_projectuser, self.user_projectmanager, self.project_pigs
        # ProjectUser: set project as template -> raise
        self.assertRaises(AccessError, project_pigs.sudo(user_projectuser.id).set_template)
        # Other tests are done using a ProjectManager
        self.assertNotEqual(project_pigs.state, 'template', 'project: incorrect state, should not be a template')
        # Set test project as template
        project_pigs.sudo(user_projectmanager.id).set_template()
        self.assertEqual(project_pigs.state, 'template', 'project: set_template: project state should be template')
        self.assertEqual(len(project_pigs.tasks), 0, 'project: set_template: project tasks should have been set inactive')
        # Duplicate template
        new_template_act = project_pigs.sudo(user_projectmanager.id).duplicate_template()
        new_project = self.Project.sudo(user_projectmanager.id).browse(new_template_act['res_id'])
        self.assertEqual(new_project.state, 'open', 'project: incorrect duplicate_template')
        self.assertEqual(len(new_project.tasks), 2, 'project: duplicating a project template should duplicate its tasks')
        # Convert into real project
        project_pigs.sudo(user_projectmanager.id).reset_project()
        self.assertEqual(project_pigs.state, 'open', 'project: resetted project should be in open state')
        self.assertEqual(len(project_pigs.tasks), 2, 'project: reset_project: project tasks should have been set active')
        # Put as pending
        project_pigs.sudo(user_projectmanager.id).set_pending()
        self.assertEqual(project_pigs.state, 'pending', 'project: should be in pending state')
        # Re-open
        project_pigs.sudo(user_projectmanager.id).set_open()
        self.assertEqual(project_pigs.state, 'open', 'project: reopened project should be in open state')
        # Close project
        project_pigs.sudo(user_projectmanager.id).set_done()
        self.assertEqual(project_pigs.state, 'close', 'project: closed project should be in close state')
        # Re-open
        project_pigs.sudo(user_projectmanager.id).set_open()
        # Re-convert into a template and schedule tasks
        project_pigs.sudo(user_projectmanager.id).set_template()
        project_pigs.sudo(user_projectmanager.id).schedule_tasks()
        # Copy the project
        new_project = project_pigs.sudo(user_projectmanager.id).copy()
        self.assertEqual(len(new_project.tasks), 2, 'project: copied project should have copied task')
        # Cancel the project
        project_pigs.sudo(user_projectmanager.id).set_cancel()
        self.assertEqual(project_pigs.state, 'cancelled', 'project: cancelled project should be in cancel state')

    def test_10_task_process(self):
        """ Testing task creation and management """
        user_projectuser, user_projectmanager, project_pigs = self.user_projectuser, self.user_projectmanager, self.project_pigs
        # create new partner
        self.partner = self.ResPartner.with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs',
            'email': 'otherid@gmail.com'})
        def format_and_process(template, email_to='project+pigs@mydomain.com, other@gmail.com', cc='otherid@gmail.com', subject='Frogs',
                               email_from='Patrick Ratatouille <patrick.ratatouille@agrolait.com>',
                               msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
            self.assertFalse(self.ProjectTask.search([('name', '=', subject)]))
            mail = template.format(email_to=email_to, cc=cc, subject=subject, email_from=email_from, msg_id=msg_id)
            self.MailThread.message_process(None, mail)
            return self.ProjectTask.search([('name', '=', subject)])
        # Do: incoming mail from an unknown partner on an alias creates a new task 'Frogs'
        task = format_and_process(EMAIL_TPL)
        # Test: one task created by mailgateway administrator
        self.assertEqual(len(task), 1, 'project: message_process: a new project.task should have been created')
        # Test: check partner in message followers
        self.assertTrue((self.partner.id in task.message_follower_ids.ids),"Partner in message cc is not added as a task followers.")
        res = task.get_metadata()[0].get('create_uid') or [None]
        self.assertEqual(res[0], self.env.uid,
                        'project: message_process: task should have been created by uid as alias_user_id is False on the alias')
        # Test: messages
        self.assertEqual(len(task.message_ids), 3,
                        'project: message_process: newly created task should have 2 messages: creation and email')
        self.assertEqual(task.message_ids[2].subtype_id.name, 'Task Created',
                        'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[1].subtype_id.name, 'Task Assigned',
                        'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[0].author_id.id, self.email_partner.id,
                        'project: message_process: second message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids[0].subject, 'Frogs',
                        'project: message_process: second message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Frogs', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id.id, self.project_pigs.id, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, 1, 'project_task: should have a stage with sequence=1')
        # Open the delegation wizard
        self.env['project.task.delegate'].with_context({
            'active_id': task.id}).sudo(user_projectuser.id).create({
            'user_id': user_projectuser.id,
            'planned_hours': 12.0,
            'planned_hours_me': 2.0,
        }).with_context({'active_id': task.id}).delegate()
        # Check delegation details
        self.assertEqual(task.planned_hours, 2, 'project_task_delegate: planned hours is not correct after delegation')
