# -*- coding: utf-8 -*-

from openerp import api, fields, models

class crm_team(models.Model):
    _inherit = 'crm.team'
    _inherits = {'mail.alias': 'alias_id'}

    resource_calendar_id = fields.Many2one(
        'resource.calendar', string="Working Time", help="Used to compute open days")
    stage_ids = fields.Many2many(
        'crm.stage', 'crm_team_stage_rel', 'team_id', 'stage_id', string='Stages')
    use_leads = fields.Boolean(
        string='Leads', default=True, help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team.")
    use_opportunities = fields.Boolean(
        string='Opportunities', default=True, help="Check this box to manage opportunities in this sales team.")
    alias_id = fields.Many2one(
        'mail.alias', string='Alias', ondelete="restrict", required=True,
        help="The email address associated with this team. New emails received will automatically create new leads assigned to the team.")

    @api.v7
    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all lead and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(crm_team, self)._auto_init,
            'crm.lead', self._columns['alias_id'], 'name', alias_prefix='Lead+', alias_defaults={}, context=context)

    def _get_stage_common(self):
        result = self.env['crm.stage'].search([('case_default', '=', 1)])
        return result.ids

    @api.model
    def create(self, vals):
        team = super(crm_team, self.with_context(
            alias_model_name='crm.lead', alias_parent_model_name=self._name)).create(vals)
        team.alias_id.write(
            {'alias_parent_thread_id': team.id, 'alias_defaults': {'team_id': team.id, 'type': 'lead'}})
        return team

    @api.multi
    def unlink(self):
        # Cascade-delete mail aliases as well, as they should not exist without the sales team.
        alias_ids = list(set(team.alias_id.id for team in self if team.alias_id))
        res = super(crm_team, self).unlink()
        self.env['mail.alias'].browse(alias_ids).unlink()
        return res
