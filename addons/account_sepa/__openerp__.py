# -*- coding: utf-8 -*-
{
    'name': "SEPA Credit Transfer",
    'summary': """Export payments as SEPA Credit Transfer files""",
    'description': """
        Generate payment orders as pain.001.001.03 messages. The generated XML file can then be uploaded to your bank.
        For more informations about the SEPA standards : http://www.iso20022.org/
    """,
    'author': "Odoo SA",
    'category': 'Accounting &amp; Finance',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'views/account_journal_view.xml',
        'views/account_register_payment_view.xml',
        'views/account_sepa_credit_transfer_view.xml',
    ],
}
