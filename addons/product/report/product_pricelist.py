# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import time
from openerp import models, api
from openerp.tools.translate import _


class report_pricelist(models.AbstractModel):
    _name = 'report.product.report_pricelist'

    @api.model
    def _get_titles(self, form):
        lst = []
        vals = {}
        qtys = 1
        for i in range(1, 6):
            if form['qty' + str(i)] != 0:
                vals['qty'+str(qtys)] = str(form['qty'+str(i)]) + ' units'
            qtys += 1
        lst.append(vals)
        return lst

    @api.model
    def _set_quantity(self, form):
        for i in range(1, 6):
            q = 'qty%d' % i
            if form[q] > 0 and form[q] not in self.quantity:
                self.quantity.append(form[q])
            else:
                self.quantity.append(0)
        return True

    @api.model
    def _get_price(self, product_ids):
        products = []
        pricelist_obj = self.env['product.pricelist']
        product_obj = self.env['product.product']
        for product in product_ids:
            val = {
                 'id': product.id,
                 'name': product.name,
                 'code': product.code
            }
            i = 1
            for qty in self.quantity:
                if qty == 0:
                    val['qty'+str(i)] = 0.0
                else:
                    price_dict = self.pricelist.price_get(product.id, qty)
                    if price_dict[self.pricelist.id]:
                        price = price_dict[self.pricelist.id]
                    else:
                        res = product_obj.browse(product.id)
                        price = res[0]['list_price']
                    val['qty' + str(i)] = price
                i += 1
            products.append(val)
        return products

    @api.model
    def _get_categories(self, products):
        cat_ids = []
        res = []
        pro_ids = []
        model_obj = self.env[self.model]
        for product in products:
            pro_ids.append(product.id)
            if product.categ_id.id not in cat_ids:
                cat_ids.append(product.categ_id.id)
        cats = self.env['product.category'].browse(cat_ids).name_get()
        if not cats:
            return res
        for cat in cats:
            product_ids = model_obj.search([('id', 'in', pro_ids), ('categ_id', '=', cat[0])])
            if self.model == 'product.template':
                products=[]
                for product in product_ids:
                    variants = self._get_price(product.product_variant_ids)
                    products.append({'name': product.name, 'variants': variants})
            else:
                products = self._get_price(product_ids)
            res.append({'name': cat[1], 'products': products})
        return res

    @api.multi
    def render_html(self, data):
        form = data.get('form')
        report_obj = self.env['report']
        self.quantity = []
        self.model = self._context.get('active_model')
        self._set_quantity(form)
        self.pricelist = self.env['product.pricelist'].browse(form['price_list'])
        selected_records = self.env[self.model].browse(data.get('ids'))
        docargs = {
            'doc_ids': data.get('ids'),
            'doc_model': self.model,
            'docs': selected_records,
            'time': time,
            'get_pricelist': self.pricelist.name,
            'get_currency': self.pricelist.currency_id.name,
            'get_titles': self._get_titles(form),
            'get_categories': self._get_categories(selected_records),
        }
        return report_obj.render('product.report_pricelist', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
