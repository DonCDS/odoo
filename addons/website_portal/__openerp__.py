# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source ERP and CRM
#    Copyright (C) 2015-Today Odoo SA (<http://www.odoo.com>).
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
    'name': 'Website Portal',
    'category': 'Website',
    'summary': 'Account Management Frontend for your Customers',
    'version': '1.0',
    'description': """
Allows your customers to manage their account from a beautiful web interface.
        """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/',
    'depends': [
        'sale',
        'website',
    ],
    'data': [
        'views/templates.xml'
    ],
    'qweb': [
    ],
    'demo': [
        'demo.xml'
    ],
    'installable': True,
    'application': True,
}
