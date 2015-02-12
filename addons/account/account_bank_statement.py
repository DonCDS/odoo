# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import osv, expression
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
from openerp.tools import float_compare, float_round
from openerp.exceptions import UserError, ValidationError

import time

class account_bank_statement(models.Model):

    @api.one
    @api.depends('line_ids', 'balance_start', 'line_ids.amount', 'balance_end_real')
    def _end_balance(self):
        self.total_entry_encoding = sum([line.amount for line in self.line_ids])
        self.balance_end = self.balance_start + self.total_entry_encoding
        self.difference = self.balance_end_real - self.balance_end

    @api.one
    @api.depends('journal_id')
    def _currency(self):
        self.currency = self.journal_id.currency or self.env.user.company_id.currency_id

    @api.one
    @api.depends('line_ids.journal_entry_ids')
    def _check_lines_reconciled(self):
        self.all_lines_reconciled = all([line.journal_entry_ids.ids or line.account_id.id for line in self.line_ids])

    @api.model
    def _default_journal(self):
        journal_type = self.env.context.get('journal_type', False)
        company_id = self.env['res.company']._company_default_get('account.bank.statement')
        if journal_type:
            journals = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)])
            if journals:
                return journals[0]
        return False

    _order = "date desc, id desc"
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "date desc, id desc"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', states={'open': [('readonly', False)]}, copy=False, default='/', readonly=True)
    # Name is readonly by default because it's the expected behaviour in cash statements, which uses inheritance by delegation
    date = fields.Date(string='Date', required=True, states={'confirm': [('readonly', True)]}, select=True, copy=False, default=fields.Date.context_today)
    date_done = fields.Datetime(string="Closed On")
    balance_start = fields.Float(string='Starting Balance', digits=0, states={'confirm': [('readonly', True)]})
    balance_end_real = fields.Float('Ending Balance', digits=0, states={'confirm': [('readonly', True)]})
    state = fields.Selection([('open', 'New'), ('confirm', 'Closed')], string='Status', required=True, readonly=True, copy=False, default='open')
    currency = fields.Many2one('res.currency', compute='_currency', string='Currency')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 states={'confirm':[('readonly',True)]}, default=_default_journal)
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))

    total_entry_encoding = fields.Float('Transactions Subtotal', compute='_end_balance', store=True, help="Total of transaction lines.")
    balance_end = fields.Float('Computed Balance', compute='_end_balance', store=True, help='Balance as calculated based on Opening Balance and transaction lines')
    difference = fields.Float(compute='_end_balance', help="Difference between the computed ending balance and the specified ending balance.")

    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines', states={'confirm': [('readonly', True)]}, copy=True)
    move_line_ids = fields.One2many('account.move.line', 'statement_id', string='Entry lines', states={'confirm': [('readonly', True)]})
    all_lines_reconciled = fields.Boolean(compute='_check_lines_reconciled')

    @api.one
    @api.constrains('state', 'balance_end', 'balance_end_real', 'difference')
    def _balance_check(self):
        if self.state == 'confirmed' and self.currency.is_zero(self.difference):
            digits = self.currency.decimal_places
            raise UserError(_('The ending balance is incorrect !\nThe expected balance (%.'+digits+'f) is different from the computed one. (%.'+digits+'f)')
                % (self.balance_end_real, self.balance_end))
        return True

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal_id = vals.get('journal_id', self._context.get('default_journal_id', False))
            journal = self.env['account.journal'].browse(journal_id)
            vals['name'] = journal.sequence_id.with_context(ir_sequence_date=vals.get('date')).next_by_id()
        return super(account_bank_statement, self).create(vals)

    @api.multi
    def unlink(self):
        for statement in self:
            if statement.state != 'open':
                raise UserError(_('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
            # Explicitly unlink bank statement lines so it will check that the related journal entries have been deleted first
            statement.line_ids.unlink()
        return super(account_bank_statement, self).unlink()

    @api.multi
    def button_cancel(self):
        for statement in self:
            if any(line.journal_entry_ids.ids for line in statement.line_ids):
                raise UserError(_('A statement cannot be canceled when its lines are reconciled.'))
        self.state = 'open'

    @api.multi
    def button_confirm_bank(self):
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            if not statement.journal_id.default_credit_account_id or not statement.journal_id.default_debit_account_id:
                raise UserError(_('Please check that a credit and a debit account are defined for the journal.'))

            moves = self.env['account.move']
            for st_line in statement.line_ids:
                if st_line.account_id and not st_line.journal_entry_ids.ids:
                    # Technical functionality to automatically reconcile by creating a new move line
                    vals = {
                        'name': st_line.name,
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                    }
                    st_line.process_reconciliation(new_aml_dicts=[vals])
                elif not st_line.journal_entry_ids.ids:
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
                moves = (moves | st_line.journal_entry_ids)
            if moves:
                moves.post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.link_bank_to_partner()
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})

    @api.multi
    def button_journal_entries(self):
        context = self._context or {}
        context['journal_id'] = self.journal_id.id
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('statement_id', 'in', self.ids)],
            'context': context,
        }

    @api.v7
    def reconciliation_widget_preprocess(self, cr, uid, statement_ids, context=None):
        return self.browse(cr, uid, statement_ids, context).reconciliation_widget_preprocess()

    @api.v8
    def reconciliation_widget_preprocess(self):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget.
        """
        statements = self
        bsl_obj = self.env['account.bank.statement.line']

        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set
        st_lines_filter = [('journal_entry_ids', '=', False), ('account_id', '=', False)]
        if statements:
            st_lines_filter += [('statement_id', 'in', statements.ids)]

        # Try to automatically reconcile statement lines
        automatic_reconciliation_entries = []
        st_lines_left = []
        for st_line in bsl_obj.search(st_lines_filter, order='statement_id, id'):
            counterpart = st_line.get_unambiguous_reconciliation_proposition()
            counterpart_amount = sum(line['debit'] for line in counterpart) - sum(line['credit'] for line in counterpart)
            st_line_amount = st_line.amount_currency if st_line.currency_id else st_line.amount
            if counterpart and counterpart_amount == st_line_amount:
                # get_reconciliation_proposition() returns informations about move lines whereas process_reconciliation()
                # expects informations about how to create new move lines to reconcile existing ones.
                # See get_reconciliation_proposition()'s docstring for more informations.
                counterpart = map(lambda l: {
                    'name': l['name'],
                    'debit': l['credit'],
                    'credit': l['debit'],
                    'move_line': self.env['account.move.line'].browse(l['id']),
                }, counterpart)
                try:
                    st_line.process_reconciliation(counterpart)
                    automatic_reconciliation_entries.append(st_line.journal_entry_ids.ids)
                except:
                    st_lines_left.append(st_line)
            else:
                st_lines_left.append(st_line)

        # Try to set statement line's partner
        for st_line in st_lines_left:
            if st_line.name and not st_line.partner_id.id:
                additional_domain = [('ref', '=', st_line.name)]
                match_ids = st_line.get_move_lines_for_bank_reconciliation(limit=1, additional_domain=additional_domain, overlook_partner=True)
                if match_ids and match_ids[0]['partner_id']:
                    st_line.write({'partner_id': match_ids[0]['partner_id']})

        # Collect various informations for the reconciliation widget
        notifications = []
        num_auto_reconciled = len(automatic_reconciliation_entries)
        if num_auto_reconciled > 0:
            auto_reconciled_message = num_auto_reconciled > 1 \
                and _("%d transactions were automatically reconciled.") % num_auto_reconciled \
                or _("1 transaction was automatically reconciled.")
            notifications += [{
                'type': 'info',
                'message': auto_reconciled_message,
                'details': {
                    'name': _("Automatically reconciled items"),
                    'model': 'account.move',
                    'ids': automatic_reconciliation_entries
                }
            }]

        return {
            'st_lines_ids': bsl_obj.search(st_lines_filter, order='statement_id, id').ids,
            'notifications': notifications,
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': statements and bsl_obj.search_count([('journal_entry_ids', '!=', False), ('id', 'in', statements.line_ids.ids)]) or 0,
        }

    @api.multi
    def link_bank_to_partner(self):
        for statement in self:
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    st_line.bank_account_id.write({'partner_id': st_line.partner_id.id})


class account_bank_statement_line(models.Model):
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _order = "statement_id desc, sequence"
    _inherit = ['ir.needaction_mixin']

    name = fields.Char(string='Communication', required=True, default=lambda self: self.env['ir.sequence'].get('account.bank.statement.line'))
    date = fields.Date(required=True, default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    amount = fields.Float(digits=0)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    account_id = fields.Many2one('account.account', string='Counterpart Account', domain=[('deprecated', '=', False)],
        help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation"
             " process on it later on. The statement line will simply create a counterpart on this account")
    statement_id = fields.Many2one('account.bank.statement', string='Statement', index=True, required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', related='statement_id.journal_id', string='Journal', store=True, readonly=True)
    partner_name = fields.Char(string='Partner Name',
        help="This field is used to record the third party name when importing bank statement in electronic format,"
             " when the partner doesn't exist yet in the database (or cannot be found).")
    ref = fields.Char(string='Reference')
    note = fields.Text(string='Notes')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.")
    company_id = fields.Many2one('res.company', related='statement_id.company_id', string='Company', store=True, readonly=True)
    journal_entry_ids = fields.One2many('account.move', 'statement_line_id', 'Journal Entries', copy=False, readonly=True)
    amount_currency = fields.Float(string='Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits=0)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The optional other currency if it is a multi-currency entry.")

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        # This constraint could possibly underline flaws in bank statement import (eg. inability to
        # support hacks such as using dummy transactions to give additional informations)
        if self.amount == 0:
            raise ValidationError('A transaction can\'t have a 0 amount.')

    @api.one
    @api.constrains('amount', 'amount_currency')
    def _check_amount_currency(self):
        if self.amount_currency != 0 and self.amount == 0:
            raise ValidationError('If "Amount Currency" is specified, then "Amount" must be as well.')

    @api.multi
    def unlink(self):
        for line in self:
            if line.journal_entry_ids.ids:
                raise UserError(_('In order to delete a bank statement line, you must first cancel it to delete related journal items.'))
        return super(account_bank_statement_line, self).unlink()

    @api.model
    def _needaction_domain_get(self):
        return [('journal_entry_ids', '=', False), ('account_id', '=', False)]

    @api.multi
    def button_cancel_reconciliation(self):
        # TOCKECK : might not behave as expected in case of reconciliations (match statement line with already
        # registered payment) or partial reconciliations.
        move_recs = self.env['account.move']
        for st_line in self:
            move_recs = (move_recs | st_line.journal_entry_ids)
        if move_recs:
            for move in move_recs:
                move.line_id.remove_move_reconcile()
            move_recs.write({'statement_line_id': False})
            move_recs.button_cancel()
            move_recs.unlink()

    @api.v7
    def get_data_for_reconciliations(self, cr, uid, ids, excluded_ids=None, context=None):
        return self.browse(cr, uid, ids, context).get_data_for_reconciliations(excluded_ids)

    @api.v8
    def get_data_for_reconciliations(self, excluded_ids=None):
        """ Returns the data required to display a reconciliation widget, for each statement line in self """
        excluded_ids = excluded_ids or []
        ret = []

        for st_line in self:
            sl = st_line.get_statement_line_for_reconciliation()
            rp = st_line.get_reconciliation_proposition(excluded_ids=excluded_ids)
            excluded_ids += [move_line['id'] for move_line in rp]
            ret.append({
                'st_line': sl,
                'reconciliation_proposition': rp
            })

        return ret

    def get_statement_line_for_reconciliation(self):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """
        statement_currency = self.journal_id.currency or self.journal_id.company_id.currency_id
        rml_parser = report_sxw.rml_parse(self._cr, self._uid, 'reconciliation_widget_asl', context=self._context)

        if self.amount_currency and self.currency_id:
            amount = self.amount_currency
            amount_currency = self.amount
            amount_currency_str = amount_currency > 0 and amount_currency or -amount_currency
            amount_currency_str = rml_parser.formatLang(amount_currency_str, currency_obj=statement_currency)
        else:
            amount = self.amount
            amount_currency_str = ""
        amount_str = amount > 0 and amount or -amount
        amount_str = rml_parser.formatLang(amount_str, currency_obj=self.currency_id or statement_currency)

        data = {
            'id': self.id,
            'ref': self.ref,
            'note': self.note or "",
            'name': self.name,
            'date': self.date,
            'amount': amount,
            'amount_str': amount_str, # Amount in the statement line currency
            'currency_id': self.currency_id.id or statement_currency.id,
            'partner_id': self.partner_id.id,
            'statement_id': self.statement_id.id,
            'account_code': self.journal_id.default_debit_account_id.code,
            'account_name': self.journal_id.default_debit_account_id.name,
            'partner_name': self.partner_id.name,
            'communication_partner_name': self.partner_name,
            'amount_currency_str': amount_currency_str, # Amount in the statement currency
            'has_no_partner': not self.partner_id.id,
        }
        if self.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = self.partner_id.property_account_receivable.id
            else:
                data['open_balance_account_id'] = self.partner_id.property_account_payable.id

        return data

    def _get_domain_maker_move_line_amount(self):
        """ Returns a function that can create the appropriate domain to search on move.line amount based on statement.line currency/amount """
        currency = self.currency_id or self.journal_id.currency
        field = currency and 'amount_residual_currency' or 'amount_residual'
        precision = currency and currency.decimal_places or self.journal_id.company_id.currency_id.decimal_places

        def ret(comparator, amount, p=precision, f=field, c=currency.id):
            if comparator == '<':
                if amount < 0:
                    domain = [(f, '<', 0), (f, '>', amount)]
                else:
                    domain = [(f, '>', 0), (f, '<', amount)]
            elif comparator == '=':
                domain = [(f, '=', float_round(amount, precision_digits=p))]
            else:
                raise osv.except_osv(_("Programmation error : domain_maker_move_line_amount requires comparator '=' or '<'"))
            domain += [('currency_id', '=', c)]
            return domain

        return ret

    def get_unambiguous_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that can without doubt be used to reconcile a statement line """

        # How to compare statement line amount and move lines amount
        amount_domain_maker = self._get_domain_maker_move_line_amount()
        equal_amount_domain = amount_domain_maker('=', self.amount_currency or self.amount)

        # Look for structured communication match
        if self.name:
            overlook_partner = not self.partner_id # If the transaction has no partner, look for match in payable and receivable account anyway
            domain = equal_amount_domain + [('ref', '=', self.name)]
            match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=2, additional_domain=domain, overlook_partner=overlook_partner)
            if match_ids and len(match_ids) == 1:
                return match_ids

        # Look for a single move line with the same partner, the same amount
        if self.partner_id:
            match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=2, additional_domain=equal_amount_domain)
            if match_ids and len(match_ids) == 1:
                return match_ids

        return []

    @api.v7
    def get_reconciliation_proposition(self, cr, uid, id, excluded_ids=None, context=None):
        return self.browse(cr, uid, id, context).get_reconciliation_proposition(excluded_ids)

    @api.v8
    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line """

        # Look for structured communication match
        if self.name:
            overlook_partner = not self.partner_id # If the transaction has no partner, look for match in payable and receivable account anyway
            domain = [('ref', '=', self.name)]
            match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=1, additional_domain=domain, overlook_partner=overlook_partner)
            if match_ids:
                return match_ids

        # How to compare statement line amount and move lines amount
        amount_domain_maker = self._get_domain_maker_move_line_amount()
        amount = self.amount_currency or self.amount

        # Look for a single move line with the same amount
        match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=1, additional_domain=amount_domain_maker('=', amount))
        if match_ids:
            return match_ids

        if not self.partner_id:
            return []

        # Look for a set of move line whose amount is <= to the line's amount
        domain = [('reconciled', '=', False)] # Make sure we can't mix reconciliation and 'rapprochement'
        domain += [('account_id.user_type.type', '=', amount > 0 and 'receivable' or 'payable')] # Make sure we can't mix receivable and payable
        domain += amount_domain_maker('<', amount) # Will also enforce > 0
        mv_lines = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=5, additional_domain=domain)
        currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
        ret = []
        total = 0
        for line in mv_lines:
            total += abs(line['debit'] - line['credit'])
            if float_compare(total, abs(amount), precision_digits=currency.rounding) != 1:
                ret.append(line)
            else:
                break
        return ret

    def _domain_move_lines_for_bank_reconciliation(self, excluded_ids=None, str=False, additional_domain=None, overlook_partner=False):
        """ Create domain criteria that are relevant to bank statement reconciliation. """

        # Domain to fetch registered payments (use case where you encode the payment before you get the bank statement)
        reconciliation_aml_accounts = [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]
        domain_reconciliation = ['&', ('statement_id', '=', False), ('account_id', 'in', reconciliation_aml_accounts)]

        # Domain to fetch unreconciled payables/receivables (use case where you close invoices/refunds by reconciling your bank statements)
        domain_matching = [('reconciled', '=', False)]
        if self.partner_id.id or overlook_partner:
            domain_matching = expression.AND([domain_matching, [('account_id.internal_type', 'in', ['payable', 'receivable'])]])
        else:
            # TODO : find out what use case this permits (match a check payment, registered on a journal whose account type is other instead of liquidity)
            domain_matching = expression.AND([domain_matching, [('account_id.reconcile', '=', True)]])

        # Let's add what applies to both
        domain = expression.OR([domain_reconciliation, domain_matching])
        if self.partner_id.id and not overlook_partner:
            domain = expression.AND([domain, [('partner_id', '=', self.partner_id.id)]])

        # Domain factorized for all reconciliation use cases
        ctx = self._context or {}
        ctx['bank_statement_line'] = self
        generic_domain = self.env['account.move.line'].with_context(ctx).domain_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str)
        domain = expression.AND([domain, generic_domain])

        # Domain from caller
        if additional_domain is None:
            additional_domain = []
        else:
            additional_domain = expression.normalize_domain(additional_domain)
        domain = expression.AND([domain, additional_domain])

        return domain

    @api.v7
    def get_move_lines_for_bank_reconciliation(self, cr, uid, st_line_id, excluded_ids=None, str=False, offset=0, limit=None, context=None):
        """ Returns move lines for the bank statement reconciliation widget, prepared as a list of dicts """
        return self.browse(cr, uid, st_line_id, context).get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, str=str, offset=offset, limit=limit)

    @api.v8
    def get_move_lines_for_bank_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None, overlook_partner=False):
        domain = self._domain_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, str=str, additional_domain=additional_domain, overlook_partner=overlook_partner)
        move_lines = self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")
        target_currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
        ret_data = move_lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=self.date)
        has_no_partner = not bool(self.partner_id.id)
        for line in ret_data:
            line['has_no_partner'] = has_no_partner
        return ret_data

    def _prepare_move(self, move_name):
        """ Prepare the dict of values to create the move from a statement line. This method may be overridden to adapt domain logic
            through model inheritance (make sure to call super() to establish a clean extension chain).

           :param char st_line_number: will be used as the name of the generated account move
           :return: dict of value to create() the account.move
        """
        return {
            'statement_line_id': self.id,
            'journal_id': self.statement_id.journal_id.id,
            'date': self.date,
            'name': move_name,
            'ref': self.ref,
        }

    def _prepare_move_line(self, move, amount):
        """ Prepare the dict of values to create the move line from a statement line.

            :param recordset move: the account.move to link the move line
            :param float amount: the amount of transaction that wasn't already reconciled
        """
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency or company_currency
        st_line_currency = self.currency_id or statement_currency

        if statement_currency == company_currency:
            amount = self.amount
        elif st_line_currency == company_currency:
            amount = self.amount_currency
        else:
            amount = statement_currency.with_context({'date': self.date}).compute(self.amount, company_currency)

        if statement_currency != company_currency:
            amount_currency = self.amount
        elif st_line_currency != company_currency:
            amount_currency = self.amount_currency
        else:
            amount_currency = False

        return {
            'name': self.name,
            'date': self.date,
            'ref': self.ref,
            'move_id': move.id,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'account_id': self.amount >= 0 \
                and self.statement_id.journal_id.default_credit_account_id.id \
                or self.statement_id.journal_id.default_debit_account_id.id,
            'credit': amount < 0 and -amount or 0.0,
            'debit': amount > 0 and amount or 0.0,
            'statement_id': self.statement_id.id,
            'journal_id': self.statement_id.journal_id.id,
            'currency_id': statement_currency != company_currency and statement_currency.id or (st_line_currency != company_currency and st_line_currency.id or False),
            'amount_currency': amount_currency,
        }

    @api.v7
    def process_reconciliations(self, cr, uid, data, context=None):
        """ Handles data sent from the bank statement reconciliation widget (and can otherwise serve as an old-API bridge)

            :param list of dicts data: must contains the keys 'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
                whose value is the same as described in process_reconciliation except that ids are used instead of recordsets.
        """
        aml_obj = self.pool['account.move.line']
        for datum in data:
            st_line = self.browse(cr, uid, datum['st_line_id'], context)
            payment_aml_rec = aml_obj.browse(cr, uid, datum['payment_aml_ids'], context)
            for aml_dict in datum['counterpart_aml_dicts']:
                aml_dict['move_line'] = aml_obj.browse(cr, uid, aml_dict['counterpart_aml_id'], context)
                del aml_dict['counterpart_aml_id']
            st_line.process_reconciliation(datum['counterpart_aml_dicts'], payment_aml_rec, datum['new_aml_dicts'])

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and refunds) and/or new move lines (eg. write-offs).
            If any new journal item needs to be created (via new_aml_dicts or counterpart_aml_dicts), a new journal entry will be created and will contain those
            items, as well as a journal item for the bank statement line.
            Finally, mark the statement line as reconciled by putting the matched moves ids in the column journal_entry_ids.
            If you feel confused about this reconciliation process (which is perfectly normal), feel free to experiment use cases and check generated journal entries.

            :param (list of dicts) counterpart_aml_dicts: move lines to create to reconcile with existing payables/receivables.
                The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'move_line'
                    # The move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)

            :param (list of recordsets) payment_aml_rec: recordset move lines representing existing payments (which are already fully reconciled)

            :param (list of dicts) new_aml_dicts: move lines to create. The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'account_id'
                - (optional) 'tax_ids'
                - (optional) Other account.move.line fields like analytic_account_id or analytics_id

            :returns: if there was at least an entry in counterpart_aml_dicts or new_aml_dicts, returns the move corresponding to the reconciliation,
                containing entries for the statement.line (1), the counterpart move lines (0..*) and the new move lines (0..*). Otherwise returns None.
        """
        counterpart_aml_dicts = counterpart_aml_dicts or []
        payment_aml_rec = payment_aml_rec or self.env['account.move.line']
        new_aml_dicts = new_aml_dicts or []
        aml_obj = self.env['account.move.line']
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency or company_currency
        st_line_currency = self.currency_id or statement_currency

        # Check and prepare received data
        if self.journal_entry_ids.ids:
            raise UserError(_('The bank statement line was already reconciled.'))
        if any(rec.statement_id for rec in payment_aml_rec):
            raise UserError(_('A selected move line was already reconciled.'))
        for aml_dict in counterpart_aml_dicts:
            if aml_dict['move_line'].reconciled:
                raise UserError(_('A selected move line was already reconciled.'))
            if isinstance(aml_dict['move_line'], (int, long)):
                aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])
            if aml_dict.get('tax_ids') and aml_dict['tax_ids'] and isinstance(aml_dict['tax_ids'][0], (int, long)):
                # Transform the value in the format required for One2many and Many2many fields
                aml_dict['tax_ids'] = map(lambda id: (4, id, None), aml_dict['tax_ids'])

        # Fully reconciled moves are just linked to the bank statement
        payment_aml_rec.write({'statement_id': self.statement_id.id})
        for aml_rec in payment_aml_rec:
            aml_rec.move_id.write({'statement_line_id': self.id})

        # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if counterpart_aml_dicts or new_aml_dicts:
            st_line_amount = self.currency_id and self.amount_currency or self.amount
            st_line_currency = self.currency_id or statement_currency
            st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False

            # Create the move
            move_name = (self.statement_id.name or self.name) + "/" + str(self.sequence)
            move_vals = self._prepare_move(move_name)
            move = self.env['account.move'].create(move_vals)

            # Create the move line for the statement line
            for aml_rec in payment_aml_rec: # Deduce already reconciled amount
                aml_amount = aml_rec.debit - aml_rec.credit
                if aml_rec.currency_id != st_line_currency:
                    aml_amount = aml_rec.currency_id.with_context({'date': self.date}).compute(aml_amount)
                st_line_amount -= aml_amount
            st_line_move_line_vals = self._prepare_move_line(move, st_line_amount)
            aml_obj.create(st_line_move_line_vals, check=False)

            ctx = self._context.copy()
            ctx['date'] = self.date
            # Complete dicts to create both counterpart move lines and write-offs
            for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
                aml_dict['ref'] = move_name
                aml_dict['move_id'] = move.id
                aml_dict['date'] = self.statement_id.date
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['journal_id'] = self.journal_id.id
                aml_dict['company_id'] = self.company_id.id
                aml_dict['statement_id'] = self.statement_id.id
                if st_line_currency.id != company_currency.id:
                    aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
                    aml_dict['currency_id'] = st_line_currency.id
                    if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                        # Statement is in company currency but the transaction is in foreign currency
                        aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                        aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
                    elif self.currency_id and st_line_currency_rate:
                        # Statement is in foreign currency and the transaction is in another one
                        aml_dict['debit'] = statement_currency.with_context(ctx).compute(aml_dict['debit'] / st_line_currency_rate, company_currency)
                        aml_dict['credit'] = statement_currency.with_context(ctx).compute(aml_dict['credit'] / st_line_currency_rate, company_currency)
                    else:
                        # Statement is in foreign currency and no extra currency is given for the transaction
                        aml_dict['debit'] = st_line_currency.with_context(ctx).compute(aml_dict['debit'], company_currency)
                        aml_dict['credit'] = st_line_currency.with_context(ctx).compute(aml_dict['credit'], company_currency)
                elif statement_currency.id != company_currency.id:
                    # Statement is in foreign currency but the transaction is in company currency
                    prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
                    aml_dict['amount_currency'] = prorata_factor * self.amount
                    aml_dict['currency_id'] = statement_currency.id

            # Complete dicts, create counterpart move lines and reconcile them
            for aml_dict in counterpart_aml_dicts:
                if aml_dict['move_line'].partner_id.id:
                    aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id # TODO : soon aml_dict['move_line'].move_id.partner_id.id
                aml_dict['account_id'] = aml_dict['move_line'].account_id.id

                counterpart_move_line = aml_dict.pop('move_line')
                if counterpart_move_line.currency_id and counterpart_move_line.currency_id != company_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = counterpart_move_line.currency_id.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], counterpart_move_line.currency_id)
                new_aml = aml_obj.create(aml_dict, check=False)
                (new_aml | counterpart_move_line).reconcile()

            # Complete dicts and create write-offs
            for aml_dict in new_aml_dicts:
                aml_obj.create(aml_dict, check=False)

            return move
        return None
