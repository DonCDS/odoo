import logging

from passlib.context import CryptContext

import openerp
from openerp import models, api, fields

_logger = logging.getLogger(__name__)

default_crypt_context = CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'md5_crypt'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Debian only provides 1.5 so...
    deprecated=['md5_crypt'],
)

class res_users(models.Model):
    _inherit = "res.users"

    #need to migrate
    def init(self, cr):
        _logger.info("Hashing passwords, may be slow for databases with many users...")
        cr.execute("SELECT id, password FROM res_users"
                   " WHERE password IS NOT NULL"
                   "   AND password != ''")
        for uid, pwd in cr.fetchall():
            self._set_password(cr, openerp.SUPERUSER_ID, uid, pwd)
    
    @api.one
    def set_pw(self):
        if self.password:
            self._set_password(self.password)
            self.invalidate_cache()

    @api.one
    def get_pw(self):
        self._cr.execute('select id, password from res_users where id in %s', (self._ids))
        return dict(self._cr.fetchall())


    password = fields.Char(compute='get_pw', inverse='set_pw', string='Password', invisible=True, store=True)
    password_crypt = fields.Char(string='Encrypted Password', invisible=True, copy=False)

    @api.model
    def check_credentials(self, password):
        # convert to base_crypt if needed
        self._cr.execute('SELECT password, password_crypt FROM res_users WHERE id=%s AND active', (self._uid,))
        encrypted = None
        if self._cr.rowcount:
            stored, encrypted = self._cr.fetchone()
            if stored and not encrypted:
                self._set_password(stored)
                self.invalidate_cache()
        try:
            return super(res_users, self).check_credentials(password)
        except openerp.exceptions.AccessDenied:
            if encrypted:
                valid_pass, replacement = self._crypt_context()\
                        .verify_and_update(password, encrypted)
                if replacement is not None:
                    self._set_encrypted_password(replacement)
                if valid_pass:
                    return
            raise

    @api.one
    def _set_password(self, password):
        """ Encrypts then stores the provided plaintext password for the user
        ``id``
        """
        encrypted = self._crypt_context().encrypt(password)
        self._set_encrypted_password(encrypted)

    @api.multi
    def _set_encrypted_password(self, encrypted):
        """ Store the provided encrypted password to the database, and clears
        any plaintext password

        :param uid: id of the current user
        :param id: id of the user on which the password should be set
        """
        self._cr.execute(
            "UPDATE res_users SET password='', password_crypt=%s WHERE id=%s",
            (encrypted, self.id))

    @api.model
    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return default_crypt_context