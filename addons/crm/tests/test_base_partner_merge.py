from openerp.tests import common

class testBasePartnerMerge(common.TransactionCase):
    def setUp(self):
        super(testBasePartnerMerge, self).setUp()

    def test_partner_merge(self):
        """ Tests for Merge Partner """
        base_partner_merge = self.env[
            'base.partner.merge.automatic.wizard']
        res_partner = self.env['res.partner']

        partner_test_merge1 = res_partner.create(
            dict(
                name="Armande Crm_User",
                city="Belgium",
                email="admin@openerp.com",
            ))

        partner_test_merge2 = res_partner.create(
            dict(
                name="Armande Crm_User",
                city="Belgium",
                email="demo@openerp.com",
            ))

        base_partner_obj = base_partner_merge.create(
            vals={'group_by_name': True})
        base_partner_obj.start_process_cb()
        base_partner_obj.merge_cb()
        partner_count = base_partner_obj.dst_partner_id.search_count(
            [('name', 'ilike', 'Armande Crm_User')])
        self.assertEqual(
            partner_count, 1, 'Crm: Partners which name have same are not succesfully merged')
