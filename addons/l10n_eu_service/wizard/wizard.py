# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (C) 2015 Odoo S.A. <http://www.odoo.com>
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

from openerp import fields, models, api
from openerp.tools.translate import _

class l10n_eu_service(models.TransientModel):

    """Create fiscal positions for EU Service VAT"""

    _name = "l10n_eu_service.wizard"
    _description = __doc__

    def _compute_default_value_chart(self):
        user = self.env.user
        return self.env['account.account'].search(
            [('company_id', '=', user.company_id.id), ('parent_id', '=', False)], limit=1)

    def _compute_default_value_fiscal_position(self):
        user = self.env.user
        eu_id = self.env.ref("base.europe").id
        return self.env['account.fiscal.position'].search(
            [('company_id', '=', user.company_id.id), ('vat_required', '=', False),
             ('country_group_id.id', '=', eu_id)], limit=1)

    def _compute_default_value_tax(self):
        user = self.env.user
        return self.env['account.tax'].search(
            [('company_id', '=', user.company_id.id), ('type_tax_use', '=', 'sale'),
             ('type', '=', 'percent'), ('account_collected_id', '!=', False),
             ('tax_code_id', '!=', False)], limit=1, order='amount')

    def _compute_default_value_done_country(self):
        user = self.env.user
        eu_country_group = self.env.ref("base.europe")
        return eu_country_group.country_ids - self._compute_default_value_todo_country() - user.company_id.country_id

    def _compute_default_value_todo_country(self):
        user = self.env.user
        eu_country_group = self.env.ref("base.europe")
        eu_fiscal = self.env['account.fiscal.position'].search(
            [('country_id', 'in', eu_country_group.country_ids.ids),
             ('vat_required', '=', False), ('auto_apply', '=', True)])
        return eu_country_group.country_ids - eu_fiscal.mapped('country_id') - user.company_id.country_id
    
    chart_id = fields.Many2one(
        "account.account", string="Chart of Accounts", required=True,
        default=_compute_default_value_chart)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, 
        related='chart_id.company_id', readonly=True)
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position',
        help="Optional fiscal position to use as template for general account mapping. "
             "Should usually be your current Intra-EU B2C fiscal position. "
             "If not set, no general account mapping will be configured for EU fiscal positions.",
        default=_compute_default_value_fiscal_position)
    tax_id = fields.Many2one(
        'account.tax', string='Service VAT', default=_compute_default_value_tax, required=True,
        help="Select your current VAT tax for services. This is the tax that will be mapped "
             "to the corresponding VAT tax in each EU country selected below.")
    account_collected_id = fields.Many2one(
        "account.account", string="Tax Collection Account",
        help="Optional account to use for collecting tax amounts when selling services in "
             "each EU country selected below. If not set, the current collecting account of "
             "you Service VAT will be used.")
    done_country_ids = fields.Many2many(
        'res.country', 'l10n_eu_service_country_rel_done',
        string='Countries already setup', default=_compute_default_value_done_country)
    todo_country_ids = fields.Many2many(
        'res.country', 'l10n_eu_service_country_rel_todo',
        string='Countries to setup', default=_compute_default_value_todo_country, required=True)

    @api.multi
    def generate_eu_service(self):
        imd = self.env['ir.model.data']
        tax_code = self.env['account.tax.code']
        tax_rate = self.env["l10n_eu_service.service_tax_rate"]
        account_tax = self.env['account.tax']
        fpos = self.env['account.fiscal.position']
        chart_xid = 'l10n_eu_service.tax_chart_service_eu_company_%s' % self.company_id.name
        chart_id = self.env.ref(chart_xid, raise_if_not_found=False).id
        if not chart_id:
            vals = {
                'name': _("EU MOSS VAT Chart - %(company)s") % {'company': self.company_id.name},
                'company_id': self.company_id.id,
                'parent_id': False
            }
            chart_id = tax_code.create(vals).id
            vals_data = {
                'name': 'tax_chart_service_eu_company_%s'%(self.company_id.name),
                'model': 'account.tax.code',
                'module': 'l10n_eu_service',
                'res_id': chart_id,
                'noupdate': True, # Don't drop it when module is updated
            }
            imd.create(vals_data)
        for country in self.todo_country_ids:
            tx_base_code_data = {
                'name': "BASE VAT for EU Services to %s" % country.name,
                'code': "EU-VAT-BASE-%s" % country.code,
                'parent_id': chart_id,
            }
            tx_code_data = {
                'name': "VAT for EU Services to %s" % country.name,
                'code': "EU-VAT-%s" % country.code,
                'parent_id': chart_id,
            }
            tx_base_code = tax_code.create(tx_base_code_data)
            tx_code = tax_code.create(tx_code_data)
            #create a new tax based on the selected service tax
            data_tax = {
                'name': "VAT for EU Services to %s" % country.name,
                'amount': tax_rate.search([('country_id', '=', country.id)]).rate,
                'base_code_id': self.tax_id.base_code_id.id,
                'account_collected_id': self.account_collected_id.id or self.tax_id.account_collected_id.id,
                'account_paid_id': self.account_collected_id.id or self.tax_id.account_collected_id.id,
                'type_tax_use': 'sale',
                'base_code_id': tx_base_code.id,
                'ref_base_code_id': tx_base_code.id,
                'tax_code_id': tx_code.id,
                'ref_tax_code_id': tx_code.id,
                'ref_base_sign': -1,
                'ref_tax_sign': -1
            }
            tax = account_tax.create(data_tax)
            if self.fiscal_position_id:
                account_ids = self.fiscal_position_id.account_ids
            else:
                account_ids = False
            #create a fiscal position for the country
            fiscal_pos_name = _("Intra-EU B2C in %(country_name)s") % {'country_name': country.name}
            fiscal_pos_name += " (EU-VAT-%s)" % country.code
            data_fiscal = {
                'name': fiscal_pos_name,
                'vat_required': False,
                'auto_apply': True,
                'country_id': country.id,
                'account_ids': account_ids,
                'tax_ids': [(0, 0, {'tax_src_id': self.tax_id.id, 'tax_dest_id': tax.id})],
            }
            fpos.create(data_fiscal)

        return {'type': 'ir.actions.act_window_close'}


