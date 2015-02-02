from openerp.osv import osv, fields

class crm_lead(osv.Model):
    _inherit = 'crm.lead'

    def __init__(self, pool, cr):
        init_crm_lead = super(crm_lead, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.CRM_LEAD_FIELDS_TO_MERGE = list(self.CRM_LEAD_FIELDS_TO_MERGE)
        self.CRM_LEAD_FIELDS_TO_MERGE.extend(['quotation_ids'])
        return init_crm_lead

    def _get_sale_amount_total(self, cr, uid, ids, fields, args, context=None):
        res = dict.fromkeys(ids, False)
        sale_rec = self.pool['sale.order'].read_group(cr, uid, [('opportunity_id', 'in', ids), ('state', '!=', 'cancel')], ['opportunity_id', 'amount_total'], ['opportunity_id'], context=context)
        for key, value in dict(map(lambda x: (x['opportunity_id'] and x['opportunity_id'][0], x['amount_total']), sale_rec)).items():
            res[key] = value
        return res

    def action_view_quotation(self, cr, uid, ids, context=None):
    # '''
    # This function returns an action that display existing quotations of given opportunity ids. It can either be a in a list or in a form view, if there is only one quotation to show.
    # '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'sale', 'action_quotations')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of quotation to display
        quote_ids = []
        for op in self.browse(cr, uid, ids, context=context):
            quote_ids += [quotation.id for quotation in op.quotation_ids]
        #choose the view_mode accordingly
        if len(quote_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, quote_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'sale', 'view_order_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = quote_ids and quote_ids[0] or False
        return result

    _columns = {
        'sale_amount_total': fields.function(_get_sale_amount_total, string="Total Amount Of Quotations", type="float"),
        'quotation_ids': fields.one2many('sale.order', 'opportunity_id', string="Quotations", readonly=True, copy=False, help="This is the list of quotations that have been generated for this opportunity. The same opportunity may have created quotations several times."),
    }
