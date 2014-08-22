# -*- coding: utf-8 -*-
{
    'name': 'Website Sale Layout',
    'version': '1.0',
    'summary': 'Web Quotation Layout, page-break, subtotals, separators',
    'description': """
        With this module you can personalize the web quotation with separators, page-breaks or subtotals.
    """,
    'author': 'Odoo SA',
    'website': 'http://www.odoo.com',
    'depends': ['sale_layout','website_quote'],
    'category': 'Website',
    'data': ['views/website_sale_layout_template.xml',
             'views/website_sale_layout.xml'],
    'installable': True,
}
