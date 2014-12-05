# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
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

from openerp.addons.mail.tests.common import TestMail
from openerp.tools import mute_logger


class TestPurchase(TestMail):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    def setUp(self):
        super(TestPurchase, self).setUp()

    def test_purchase_to_invoice(self):
        """ Testing for invoice create,validate and pay with invoicing and payment user."""
        # Usefull models
        IrModelData = self.env['ir.model.data']
        # Usefull record id
        group_id = IrModelData.xmlid_to_res_id('account.group_account_invoice') or False
        product_id = IrModelData.xmlid_to_res_id('product.product_category_5') or False
        company_id = IrModelData.xmlid_to_res_id('base.main_company') or False
        location_id = IrModelData.xmlid_to_res_id('stock.stock_location_3') or False
        # In order to test, I create new user and applied Invoicing & Payments group.
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test@test.com',
            'company_id': company_id,
            'groups_id': [(6, 0, [group_id])]})
        assert user, "User will not created."
        # I create partner for purchase order.
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com'})
        # In order to test I create purchase order and confirmed it.
        order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'location_id': location_id,
            'pricelist_id': 1})
        self.env['purchase.order.line'].create({
            'order_id': order.id,
            'product_id': product_id,
            'product_qty': 100.0,
            'product_uom': 1,
            'price_unit': 89.0,
            'name': 'Service',
            'date_planned': '2014-05-31'})
        assert order, "purchase order will not created."
        context = {"active_model": 'purchase.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).wkf_confirm_order()
        # In order to test I create invoice.
        invoice = order.with_context(context).action_invoice_create()
        assert invoice, "No any invoice is created for this purchase order"
        # In order to test I validate invoice wihth Test User(invoicing and payment).
        res = self.env['account.invoice'].browse(invoice).with_context(context).invoice_validate()
        self.assertTrue(res, 'Invoice will not validated')
