# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from openerp import models, fields, api
from openerp.osv import expression
from openerp.exceptions import AccessError

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.one
    def _get_description_short(self):
        for message in self:
            if message.subject:
                detail = message.subject
            else:
                plaintext_ct = '' if not message.body else html2plaintext(message.body)
                detail = plaintext_ct[:30] + '%s' % (' [...]' if len(plaintext_ct) >= 30 else '')
        self.description = detail

    description = fields.Char(compute='_get_description_short',
                              help='Message description: either the subject, or the beginning of the body'
                              )
    website_published = fields.Boolean('Published', 
                                       help="Visible on the website as a comment", copy=False
                                       )

    @api.model
    def default_get(self, fields_list):
        defaults = super(MailMessage, self).default_get(fields_list)
        # Note: explicitly implemented in default_get() instead of _defaults,
        # to avoid setting to True for all existing messages during upgrades.
        # TODO: this default should probably be dynamic according to the model
        # on which the messages are attached, thus moved to create().
        
        if 'website_published' in fields_list:
            defaults.setdefault('website_published', True)

        return defaults

    @api.model
    def _search(self, args, offset=0, limit=None, order=None,
                count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to restrict
        messages to published messages for public users. """
        if self._uid != SUPERUSER_ID:
            group_ids = self.env['res.users'].browse(self._uid).groups_id
            group_user_id = self.env["ir.model.data"].get_object_reference('base', 'group_public')[1]
            if group_user_id in [group.id for group in group_ids]:
                args = expression.AND([[('website_published', '=', True)], list(args)])

        return super(MailMessage, self)._search(args, offset=offset, limit=limit, order=order,
                                                count=count, access_rights_uid=access_rights_uid)

    @api.multi
    def check_access_rule(self, operation):
        """ Add Access rules of mail.message for non-employee user:
            - read:
                - raise if the type is comment and subtype NULL (internal note)
        """
        if self._uid != SUPERUSER_ID:
            group_ids = self.env['res.users'].browse(self._uid).groups_id
            group_user_id = self.env["ir.model.data"].get_object_reference('base', 'group_public')[1]
            if group_user_id in [group.id for group in group_ids]:
                self._cr.execute('SELECT id FROM "%s" WHERE website_published IS FALSE AND id = ANY (%%s)' % (self._table), (self.ids,))
                if self._cr.fetchall():
                    raise AccessError(_('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % (self._description, operation))
        return super(MailMessage, self).check_access_rule(operation=operation)
