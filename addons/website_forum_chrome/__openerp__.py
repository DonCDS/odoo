# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenERP S.A. (<https://www.odoo.com>).
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

{
    'name': 'Website Forum Chrome',
    'version': '1.0',
    'category': 'Website',
    'description': """
Submit Links to Forum
======================

This module lets you submit the URL to forum as a link.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com',
    'images': [],
    'depends': ['website_forum'],
    'data': [
             'views/forum_chrome.xml',
             'views/website_forum_chrome.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
}
