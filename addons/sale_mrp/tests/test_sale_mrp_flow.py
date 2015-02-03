# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.tests import common
from datetime import datetime


class TestSaleMrpFlow(common.TransactionCase):

    def test_00_sale_mrp_flow(self):
        """Test sale_mrp flow with diffrent unit of measure."""
        # Usefull models
        self.IrModelData = self.env['ir.model.data']
        self.SaleOrderLine = self.env['sale.order.line']
        self.SaleOrder = self.env['sale.order']
        self.MrpBom = self.env['mrp.bom']
        self.StockMove = self.env['stock.move']
        self.MrpBomLine = self.env['mrp.bom.line']
        self.UomObj = self.env['product.uom']
        self.ProductionOrder = self.env['mrp.production']
        self.Product = self.env['product.product']
        self.ProcurementOrder = self.env['procurement.order']
        self.Inventory = self.env['stock.inventory']
        self.InventoryLine = self.env['stock.inventory.line']
        self.ProductProduce = self.env['mrp.product.produce']

        partner_agrolite_id = self.IrModelData.xmlid_to_res_id('base.res_partner_2')
        self.categ_unit = self.IrModelData.xmlid_to_res_id('product.product_uom_categ_unit')
        self.categ_kgm = self.IrModelData.xmlid_to_res_id('product.product_uom_categ_kgm')
        self.stock_location = self.IrModelData.xmlid_to_res_id('stock.stock_location_stock')
        warehouse = self.IrModelData.xmlid_to_object('stock.warehouse0')
        route_manufacture = warehouse.manufacture_pull_id.route_id.id
        route_mto = warehouse.mto_pull_id.route_id.id

        self.uom_kg = self.UomObj.create({
            'name': 'Test-KG',
            'category_id': self.categ_kgm,
            'factor_inv': 1,
            'factor': 1,
            'uom_type': 'reference',
            'rounding': 0.000001})
        self.uom_gm = self.UomObj.create({
            'name': 'Test-G',
            'category_id': self.categ_kgm,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})
        # Check Unit
        self.uom_unit = self.UomObj.create({
            'name': 'Test-Unit',
            'category_id': self.categ_unit,
            'factor': 1,
            'uom_type': 'reference',
            'rounding': 1.0})
        self.uom_dozen = self.UomObj.create({
            'name': 'Test-DozenA',
            'category_id': self.categ_unit,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})

        # Create product C.
        # ------------------
        product_c = self.Product.create({
            'type': 'product',
            'name': 'Product C',
            'uom_id': self.uom_kg.id,
            'uom_po_id': self.uom_kg.id})

        # Create product B and its bill of metrial.
        # ----------------------------------------
        product_b = self.Product.create({
            'name': 'Product B',
            'type': 'product',
            'uom_id': self.uom_dozen.id,
            'uom_po_id': self.uom_dozen.id,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})

        # Bill of Metrial Product B.
        bom_b = self.MrpBom.create({
            'name': product_b.name,
            'product_tmpl_id': product_b.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom': self.uom_unit.id,
            'product_efficiency': 1.0,
            'type': 'phantom'})

        self.MrpBomLine.create({
            'product_id': product_c.id,
            'product_qty': 0.400,
            'bom_id': bom_b.id,
            'product_uom': self.uom_kg.id})

        # Create product D and its bill of metrial.
        # ----------------------------------------
        product_d = self.Product.create({
            'name': 'Product D',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})
        # Bill of Metrial Product D.
        bom_d = self.MrpBom.create({
            'name': product_d.name,
            'product_tmpl_id': product_d.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom': self.uom_unit.id,
            'product_efficiency': 1.0,
            'type': 'normal'})

        self.MrpBomLine.create({
            'product_id': product_c.id,
            'product_qty': 1,
            'bom_id': bom_d.id,
            'product_uom': self.uom_kg.id})

        # Create product A and its bill of metrial.
        # ----------------------------------------
        product_a = self.Product.create({
            'name': 'Product A',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})

        # Bill of Metrial Product A.
        bom_a = self.MrpBom.create({
            'name': product_d.name,
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'product_qty': 2,
            'product_uom': self.uom_dozen.id,
            'product_efficiency': 1.0,
            'type': 'normal'})

        self.MrpBomLine.create({
            'product_id': product_b.id,
            'product_qty': 3,
            'type': 'phantom',
            'bom_id': bom_a.id,
            'product_uom': self.uom_unit.id})

        self.MrpBomLine.create({
            'product_id': product_c.id,
            'product_qty': 300.5,
            'type': 'normal',
            'bom_id': bom_a.id,
            'product_uom': self.uom_gm.id})

        self.MrpBomLine.create({
            'product_id': product_d.id,
            'product_qty': 4,
            'type': 'phantom',
            'bom_id': bom_a.id,
            'product_uom': self.uom_unit.id})

        self.MrpBomLine.create({
            'product_id': product_d.id,
            'product_qty': 4,
            'type': 'normal',
            'bom_id': bom_a.id,
            'product_uom': self.uom_unit.id})
        # ----------------------------------------
        # Create Sale order of 10 Dozen product A.
        # ----------------------------------------
        order = self.SaleOrder.create({
            'partner_id': partner_agrolite_id,
            'date_order': datetime.today(),
        })
        self.SaleOrderLine.create({
            'order_id': order.id,
            'product_id': product_a.id,
            'product_uom_qty': 10,
            'product_uom': self.uom_dozen.id
        })
        assert order, "Sale order will not created."
        context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).action_button_confirm()

        # Run procurement.
        # ---------------
        proc_ids = self.ProcurementOrder.search([('origin', 'like', order.name)])
        proc_ids.run()

        # ----------------------------------------------------
        # Check production order for product A.
        # ----------------------------------------------------

        mo_a = self.ProductionOrder.search([('origin', 'like', order.name), ('product_id', '=', product_a.id)])
        self.assertEqual(len(mo_a), 1, 'Production order not created.')
        # Check quantity, unit of measure and state of production order.
        self.assertEqual(mo_a.product_id.id, product_a.id, 'Wrong product in production order.')
        self.assertEqual(mo_a.product_qty, 10, 'Wrong product quantity in production order.')
        self.assertEqual(mo_a.product_uom.id, self.uom_dozen.id, 'Wrong unit of measure in production order.')
        self.assertEqual(mo_a.state, 'confirmed', 'Production order should be confirmed.')

        # Check move lines of production order for product A.
        #  --------------------------------------------------

        # Check move lines for product c with uom kg.
        moves = self.StockMove.search([
            ('origin', 'like', mo_a.name),
            ('product_id', '=', product_c.id),
            ('product_uom', '=', self.uom_kg.id)])
        self.assertEqual(len(moves), 2, 'Production lines are not generated proper.')
        list_qty = [move.product_uom_qty for move in moves]
        # Check quantity of product c.
        self.assertEqual(set(list_qty), set([6.0, 20.0]), 'Wrong product quantity in move line of production order.')
        # Check move lines for product c with uom gm.
        move = self.StockMove.search([
            ('origin', 'like', mo_a.name),
            ('product_id', '=', product_c.id),
            ('product_uom', '=', self.uom_gm.id)])
        self.assertEqual(len(move), 1, 'Production lines are not generated proper.')
        # Check quantity of product c.
        self.assertEqual(move.product_uom_qty, 1502.5, 'Wrong quantity in move lines of production order.')
        # Check state in move lines for product c.
        moves = self.StockMove.search([
            ('origin', 'like', mo_a.name),
            ('product_id', '=', product_c.id)])
        self.assertEqual(len(moves), 3, 'Production lines are not generated proper.')
        for move in moves:
            self.assertEqual(move.state, 'confirmed', 'Wrong state in move line of production order.')
        move = self.StockMove.search([
            ('origin', 'like', mo_a.name),
            ('product_id', '=', product_d.id)])
        self.assertEqual(len(move), 1, 'Production lines are not generated proper.')
        self.assertEqual(move.state, 'waiting', 'Wrong state in move line of production order.')
        self.assertEqual(move.product_uom_qty, 20, 'Wrong quantity in move line of production order.')

        # -----------------------------------------------------------------------------------------
        # Production Order for product D.
        # -----------------------------------------------------------------------------------------

        # run procurement for product D.
        proc_d = self.ProcurementOrder.search([('origin', 'like', mo_a.name)])
        proc_d.run()
        # Check production order created or not for Product D.
        mo_d = self.ProductionOrder.search([('origin', 'like', mo_a.name), ('product_id', '=', product_d.id)])
        # Check manufacture order move states and quantity of product D.
        move = self.StockMove.search([('origin','like',mo_d.name),('product_id', '=', product_c.id)])
        self.assertEqual(mo_d.state, 'confirmed', 'Production order should be confirmed.')
        self.assertEqual(len(move), 1, 'Production lines are not generated proper.')
        self.assertEqual(move.product_id.id, product_c.id, 'Wrong product in move line of production order.')
        self.assertEqual(move.product_uom_qty, 20, 'Wrong quantity in move line of production order.')
        self.assertEqual(move.product_uom.id, self.uom_kg.id, 'Wrong unit of measure in move line of production order.')
        self.assertEqual(move.state, 'confirmed', 'Wrong state in move line of production order.')

        # -------------------------------
        # Create Inventory for product c.
        # -------------------------------

        inventory = self.Inventory.create({
            'name': 'Inventory Product KG',
            'product_id': product_c.id,
            'filter': 'product'})

        inventory.prepare_inventory()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_c.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 20,
            'location_id': self.stock_location})
        inventory.action_done()

        # --------------------------------------------------
        # Assign product c to production order of product D.
        # --------------------------------------------------

        mo_d.action_assign()
        self.assertEqual(mo_d.state, 'ready', 'Production order should be ready.')
        move = self.StockMove.search([('origin', 'like', mo_d.name), ('product_id', '=', product_c.id)])
        self.assertEqual(move.state, 'assigned', 'Wrong move line state of production order.')
        # produce product D.
        # ------------------

        produce_d = self.ProductProduce.with_context({'active_ids': [mo_d.id], 'active_id': mo_d.id}).create({
            'mode': 'consume_produce',
            'product_qty': 20})
        lines = produce_d.on_change_qty(mo_d.product_qty, [])
        produce_d.write(lines['value'])
        produce_d.do_produce()
        # Check state of production order
        self.assertEqual(mo_d.state, 'done', 'Production order should be done.')
        # Check available quantity of product D.
        self.assertEqual(product_d.qty_available, 20, 'Wrong quantity available of product D.')

        # --------------------------------------------------
        # Assign product D to production order of product A.
        # --------------------------------------------------

        mo_a.action_assign()
        self.assertEqual(mo_a.state, 'confirmed', 'Production order should be confirmed.')
        move = self.StockMove.search([('origin', 'like', mo_a.name), ('product_id', '=', product_d.id)])
        self.assertEqual(move.state, 'assigned', 'Wrong move line state of production order.')

        # Create Inventry for product C
        inventory = self.Inventory.create({
            'name': 'Inventory Product C KG',
            'product_id': product_c.id,
            'filter': 'product'})

        inventory.prepare_inventory()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_c.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 27.5025,
            'location_id': self.stock_location})
        inventory.action_done()
        # Assign product C to production order of product A.
        mo_a.action_assign()
        self.assertEqual(mo_a.state, 'ready', 'Production order should be ready.')
        moves = self.StockMove.search([('origin', 'like', mo_a.name), ('product_id', '=', product_c.id)])
        # Check product c move line state.
        for move in moves:
            self.assertEqual(move.state, 'assigned', 'Wrong move line state of production order.')

        # produce product A.
        # ------------------

        produce_a = self.ProductProduce.with_context({
            'active_ids': [mo_a.id], 'active_id': mo_a.id}).create({
                'mode': 'consume_produce'})
        lines = produce_a.on_change_qty(mo_a.product_qty, [])
        produce_a.write(lines['value'])
        produce_a.do_produce()
        # Check state of production order
        self.assertEqual(mo_a.state, 'done', 'Production order should be done.')
        # Check available quantity of product A.
        self.assertEqual(product_a.qty_available, 120, 'Wrong quantity available of product.')
