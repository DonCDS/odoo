# -*- coding: utf-8 -*-
{
    'name': "project_forecast_holidays",

    'summary': """
        make the link between forecast and hr holidays""",

    'description': """
        make the link between forecast and hr holidays
    """,

    'author': "OpenERP s.a.",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['project_forecast', 'hr_holidays'],
    'auto_install': True,

}
