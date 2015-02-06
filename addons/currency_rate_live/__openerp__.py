# -*- coding: utf-8 -*-
{
    "name" : "currency rate live",
    "version" : "1.0",
    "author" : "Odoo S.A.",
    "category" : "Financial Management/Configuration",
    "description": """Import exchange rates from the Internet.

""",
    "depends" : [
        "base",
        "account", #Added to ensure account security groups are present
        ],
    "data" : [
        "views/company_view.xml",
        "views/currency_rate_update.xml",
        "security/ir.model.access.csv"
        ],
    "demo" : [],
    "active": False,
    'installable': True
}
