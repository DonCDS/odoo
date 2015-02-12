# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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
import openerp

from openerp import api, fields, models, _
from openerp.tools.translate import _
from openerp.exceptions import UserError

class sale_configuration(models.TransientModel):
    _inherit = 'sale.config.settings'

   
    group_template_required = fields.Boolean(string="Mandatory use of templates.",
        implied_group='account_analytic_analysis.group_template_required',
        help="Allows you to set the template field as required when creating an analytic account or a contract.")
    time_unit = fields.Many2one('product.uom', string='The default working time unit.')
    
    @api.model
    def default_get(self):
        ir_model_data = self.pool.get('ir.model.data')
        res = super(sale_configuration, self).default_get(cr, uid, fields, context)
        if res.get('module_project'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            res['time_unit'] = user.company_id.project_time_mode_id.id
        else:
            product = ir_model_data.xmlid_to_object(cr, uid, 'product.product_product_consultant')
            if product and product.exists():
                res['time_unit'] = product.uom_id.id
        res['timesheet'] = res.get('module_account_analytic_analysis')
        return res

    @api.model
    def set_sale_defaults(self):
        ir_model_data = self.pool.get('ir.model.data')
        wizard = self.browse(cr, uid, ids)[0]

        if wizard.time_unit:
            product = ir_model_data.xmlid_to_object(cr, uid, 'product.product_product_consultant')
            if product and product.exists():
                product.write({'uom_id': wizard.time_unit.id, 'uom_po_id': wizard.time_unit.id})
            else:
                _logger.info("Product with xml_id 'product.product_product_consultant' not found, UoMs not updated!")
                raise UserError(_("Product with xml_id 'product.product_product_consultant' not found, UoMs not updated!"))

        if wizard.module_project and wizard.time_unit:
            user = self.pool.get('res.users').browse(cr, uid, uid, context)
            user.company_id.write({'project_time_mode_id': wizard.time_unit.id})
        res = super(sale_configuration, self).set_sale_defaults(cr, uid, ids, context)
        return res
