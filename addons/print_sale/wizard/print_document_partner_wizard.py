# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import Warning


class print_document_partner_wizard(models.TransientModel):

    _name = 'print.document.partner.wizard'

    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id

    @api.model
    def _default_print_provider(self):
        return self.env['ir.values'].get_default('print.order', 'provider_id')

    @api.one
    @api.depends('print_document_partner_line_wizard_ids')
    def _compute_sendable(self):
        for line in self.print_document_partner_line_wizard_ids:
            if not line.is_sendable:
                self.is_sendable = False
                return
        self.is_sendable = True


    # --------------------------------------------------
    # MODEL FIELDS
    # --------------------------------------------------
    is_sendable = fields.Boolean(string='Is sendable', readonly=True, compute=_compute_sendable)
    ink = fields.Selection([('BW', 'Black & White'), ('CL', 'Colour')], "Ink", default='BW')
    paper_weight = fields.Integer("Paper Weight", default=80, readonly=True)
    provider_id = fields.Many2one('print.provider', 'Print Provider', required=True, default=_default_print_provider)
    provider_balance = fields.Float("Provider Credit", digits=(16, 2))
    provider_environment = fields.Selection([('test', 'Test'), ('production', 'Production')], "Environment", default='test')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=_default_currency)

    ir_attachment_ids = fields.Many2many('ir.attachment', string='Documents', domain=[('mimetype', '=', 'application/pdf')])
    print_document_partner_line_wizard_ids = fields.One2many('print.document.partner.line.wizard', 'print_document_partner_wizard_id', string='Lines')


    @api.onchange('provider_id')
    def _onchange_provider_id(self):
        self.provider_balance = self.provider_id.balance
        self.provider_environment = self.provider_id.environment

    # --------------------------------------------------
    # METHODS
    # --------------------------------------------------
    @api.model
    def default_get(self, fields):
        """ create the lines on the wizard """
        res = super(print_document_partner_wizard, self).default_get(fields)

        active_ids = self._context.get('active_ids', [])
        active_model = self._context.get('active_model')

        if active_ids and active_model == 'res.partner':
            # create order lines
            lines = []
            for rec in self.env[active_model].browse(active_ids):
                lines.append((0, 0, {
                    'partner_id': rec.id,
                    'is_sendable' : rec.is_address_valid
                }))
            res['print_document_partner_line_wizard_ids'] = lines
        return res

    @api.multi
    def action_apply(self):
        Print_order = self.env['print.order']
        for wizard in self:
            # raise warning if the provider is not configured
            wizard.provider_id.check_configuration()
            # don't do anything if the balance is too small in the production mode (in test mode, allow all)
            if wizard.provider_balance <= 0.0 and wizard.provider_environment == 'production':
                raise Warning(_('Your credit provider is too small. Please, configure your account (> Settings > Print Provider), and put some credit on your account.'))
            for attachment in wizard.ir_attachment_ids:
                for line in wizard.print_document_partner_line_wizard_ids:
                    Print_order.create({
                        'ink' : wizard.ink,
                        'paper_weight' : wizard.paper_weight,
                        'provider_id' : wizard.provider_id.id,
                        'currency_id' : wizard.currency_id.id,
                        'user_id' : self._uid,
                        'attachment_id' : attachment.id,
                        # duplicate partner infos
                        'partner_id' : line.partner_id.id,
                        'partner_name' : line.partner_id.name,
                        'partner_street' : line.partner_id.street,
                        'partner_street2' : line.partner_id.street2,
                        'partner_state_id' : line.partner_id.state_id.id,
                        'partner_zip' : line.partner_id.zip,
                        'partner_city' : line.partner_id.city,
                        'partner_country_id' : line.partner_id.country_id.id,
                    })
        return {'type': 'ir.actions.act_window_close'}



class print_document_partner_line_wizard(models.TransientModel):

    _name = 'print.document.partner.line.wizard'

    @api.one
    @api.depends('partner_id')
    def _compute_sendable(self):
        self.is_sendable = self.partner_id.is_address_valid

    # --------------------------------------------------
    # MODEL FIELDS
    # --------------------------------------------------
    print_document_partner_wizard_id = fields.Many2one('print.document.partner.wizard', 'Print Order Wizard')
    partner_id = fields.Many2one('res.partner', 'Recipient partner')
    is_sendable = fields.Boolean(string='Is sendable', readonly=True, compute=_compute_sendable)
