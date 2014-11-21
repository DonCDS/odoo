# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
import re
from openerp.exceptions import UserError


class crm_lead2opportunity_partner(models.TransientModel):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.partner.binding'

    name = fields.Selection([
        ('convert', 'Convert to opportunity'),
        ('merge', 'Merge with existing opportunities')
    ], string='Conversion Action', required=True)
    opportunity_ids = fields.Many2many('crm.lead', string='Opportunities')
    user_id = fields.Many2one('res.users', string='Salesperson', select=True)
    team_id = fields.Many2one(
        'crm.team', string='Sales Team', oldname='section_id', select=True)

    @api.onchange('action')
    def onchange_action(self):
        self.partner_id = False if self.action != 'exist' else self._find_matching_partner(
        )

    @api.model
    def _get_duplicated_leads(self, partner_id, email, include_lost=False):
        """
        Search for opportunities that have the same partner and that arent done or cancelled
        """
        return self.env['crm.lead']._get_duplicated_leads_by_emails(partner_id, email, include_lost=include_lost)

    @api.model
    def default_get(self, fields):
        """
        Default get for name, opportunity_ids.
        If there is an exisitng partner link to the lead, find all existing
        opportunities links with this partner to merge all information together
        """
        res = super(crm_lead2opportunity_partner, self).default_get(fields)
        if self._context.get('active_id'):
            tomerge = [int(self._context['active_id'])]
            partner_id = res.get('partner_id')
            lead = self.env['crm.lead'].browse(int(self._context['active_id']))
            email = lead.partner_id and lead.partner_id.email or lead.email_from
            duplicate_lead = self._get_duplicated_leads(
                partner_id, email, include_lost=True)
            tomerge.extend(duplicate_lead and duplicate_lead.ids or [])
            tomerge = list(set(tomerge))

            if 'action' in fields and not res.get('action'):
                res['action'] = partner_id and 'exist' or 'create'
            if 'partner_id' in fields:
                res['partner_id'] = partner_id
            if 'name' in fields:
                res['name'] = len(tomerge) >= 2 and 'merge' or 'convert'
            if 'opportunity_ids' in fields and len(tomerge) >= 2:
                res['opportunity_ids'] = tomerge
            if lead.user_id:
                res['user_id'] = lead.user_id.id
            if lead.team_id:
                res['team_id'] = lead.team_id.id

        return res

    @api.onchange('user_id')
    def on_change_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = self.team_id.id
        if self.user_id:
            if self.team_id:
                user_in_team = self.env['crm.team'].search(
                    [('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)], count=True)
            else:
                user_in_team = False
            if not user_in_team:
                crm_lead = self.env['crm.lead'].browse(
                    self._context.get('active_id'))
                crm_lead.user_id = self.user_id
                crm_lead.on_change_user()
                team_id = crm_lead.team_id
        self.team_id = team_id

    @api.model
    def view_init(self, fields):
        """
        Check some preconditions before the wizard executes.
        """
        for lead in self.env['crm.lead'].browse(self._context.get('active_ids', [])):
            if lead.probability == 100:
                raise UserError(_("Closed/Dead leads cannot be converted into opportunities."))
        return False

    @api.multi
    def _convert_opportunity(self, vals):
        res = False
        lead_rec = vals.get('lead_ids', [])
        team_id = vals.get('team_id', False)
        partner_id = vals.get('partner_id', False)
        for lead in lead_rec:
            partner_id = self._create_partner(lead, self.action, partner_id or lead.partner_id.id)
            res = lead.convert_opportunity(partner_id, [], False)
        user_ids = vals.get('user_ids', False)

        if self._context.get('no_force_assignation'):
            leads_to_allocate = lead_rec.filtered(lambda l: not l.user_id)
        else:
            leads_to_allocate = lead_rec
        if user_ids:
            leads_to_allocate.allocate_salesman(user_ids, team_id=team_id)
        return res

    @api.one
    def action_apply(self):
        """
        Convert lead to opportunity or merge lead and opportunity and open
        the freshly created opportunity view.
        """
        context =  self._context
        vals = {
            'team_id': self.team_id.id,
        }
        if self.partner_id:
            vals['partner_id'] = self.partner_id.id
        if self.name == 'merge':
            lead = self.opportunity_ids.merge_opportunity()
            lead_rec = [lead]
            if lead.type == "lead":
                vals.update({'lead_ids': lead_rec, 'user_ids': [self.user_id.id]})
                self.with_context(active_ids=[lead.id])._convert_opportunity(vals)
            elif not context.get('no_force_assignation') or not lead.user_id:
                vals.update({'user_id': self.user_id.id})
                lead.write(vals)
        else:
            lead_ids = self._context.get('active_ids', [])
            lead_rec = self.env['crm.lead'].browse(lead_ids)
            vals.update({'lead_ids': lead_rec, 'user_ids': [self.user_id.id]})
            self._convert_opportunity(vals)

        return lead_rec[0].redirect_opportunity_view()

    @api.one
    def _create_partner(self, lead, action, partner_id):
        """
        Create partner based on action.
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        # TODO this method in only called by crm_lead2opportunity_partner
        # wizard and would probably diserve to be refactored or at least
        # moved to a better place
        partner = partner_id
        if self.action == 'each_exist_or_create':
            partner = self.with_context(
                active_id=lead.id)._find_matching_partner()
            action = 'create'

        res = lead.handle_partner_assignation(action, partner)
        return res.get(lead.id)


class crm_lead2opportunity_mass_convert(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Mass Lead To Opportunity Partner'
    _inherit = 'crm.lead2opportunity.partner'

    user_ids = fields.Many2many(
        'res.users', string='Salesmen', oldname='section_id')
    team_id = fields.Many2one('crm.team', string='Sales Team')
    deduplicate = fields.Boolean(
        string='Apply deduplication', help='Merge with existing leads/opportunities of each partner', default=True)
    action = fields.Selection([
        ('each_exist_or_create', 'Use existing partner or create'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', required=True)
    force_assignation = fields.Boolean(
        string='Force assignation', help='If unchecked, this will leave the salesman of duplicated opportunities')

    @api.model
    def default_get(self, fields):
        res = super(
            crm_lead2opportunity_mass_convert, self).default_get(fields)
        if 'partner_id' in fields:
            # avoid forcing the partner of the first lead as default
            res['partner_id'] = False
        if 'action' in fields:
            res['action'] = 'each_exist_or_create'
        if 'name' in fields:
            res['name'] = 'convert'
        if 'opportunity_ids' in fields:
            res['opportunity_ids'] = False
        return res

    @api.onchange('action')
    def on_change_action(self):
        if self.action != 'exist':
            self.partner_id = False

    @api.onchange('deduplicate')
    def on_change_deduplicate(self):
        active_leads = self.env['crm.lead'].browse(self._context['active_ids'])
        partner_ids = [(lead.partner_id.id, lead.partner_id and lead.partner_id.email or lead.email_from)
                       for lead in active_leads]
        partners_duplicated_leads = {}
        for partner_id, email in partner_ids:
            duplicated_leads = self._get_duplicated_leads(partner_id, email)
            if len(duplicated_leads) > 1:
                partners_duplicated_leads.setdefault((partner_id, email), []).extend(duplicated_leads.ids)
        leads_with_duplicates = []
        for lead in active_leads:
            lead_tuple = (lead.partner_id.id, lead.partner_id.email if lead.partner_id else lead.email_from)
            if len(partners_duplicated_leads.get(lead_tuple, [])) > 1:
                leads_with_duplicates.append(lead.id)
        self.opportunity_ids = leads_with_duplicates

    @api.multi
    def _convert_opportunity(self, vals):
        """
        When "massively" (more than one at a time) converting leads to
        opportunities, check the salesteam_id and salesmen_ids and update
        the values before calling super.
        """
        self.ensure_one()
        salesteam_id = self.team_id and self.team_id.id or False
        salesmen_ids = []
        if self.user_ids:
            salesmen_ids = self.user_ids.ids
        vals.update({'user_ids': salesmen_ids, 'team_id': salesteam_id})
        return super(crm_lead2opportunity_mass_convert, self)._convert_opportunity(vals)

    @api.multi
    def mass_convert(self):
        self.ensure_one()
        if self.name == 'convert' and self.deduplicate:
            merged_lead_ids = []
            remaining_lead_ids = []
            lead_selected = self._context.get('active_ids', [])
            for lead_id in lead_selected:
                if lead_id not in merged_lead_ids:
                    lead = self.env['crm.lead'].browse(lead_id)
                    duplicated_lead_rec = self._get_duplicated_leads(
                        lead.partner_id.id, lead.partner_id and lead.partner_id.email or lead.email_from)
                    if len(duplicated_lead_rec.ids) > 1:
                        duplicated_lead_rec = duplicated_lead_rec.sorted()
                        lead = duplicated_lead_rec.merge_opportunity()
                        merged_lead_ids.extend(duplicated_lead_rec.ids)
                        remaining_lead_ids.append(lead.id)

            active_ids = set(self._context.get('active_ids', []))
            active_ids = active_ids.difference(merged_lead_ids)
            active_ids = active_ids.union(remaining_lead_ids)
            self = self.with_context(active_ids=list(active_ids))
        self = self.with_context(no_force_assignation=self._context.get(
            'no_force_assignation', not self.force_assignation))
        return self.action_apply()[0]
