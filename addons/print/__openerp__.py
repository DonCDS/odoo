# -*- coding: utf-8 -*-
{
    'name': 'Print Invoice',
    'summary': 'Print and Send Provider Base Module',
    'category': 'Tools',
    'version': '1.0',
    'description': """Print and Send Provider Base Module. Print and send your invoice with a Postal Provider. This required to install a module implementing a provider.""",
    'author': 'Odoo SA',
    'depends': ['base_setup', 'account'],
    'data': [
        'wizard/print_order_wizard.xml',
        'wizard/print_order_sendnow_wizard.xml',
        'views/print_view.xml',
        'views/res_config_view.xml',
        'views/account_invoice_view.xml',
        'data/print_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
