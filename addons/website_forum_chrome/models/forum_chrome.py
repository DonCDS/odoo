import os
import shutil
import tempfile
import zipfile

import openerp
from openerp import api, fields, models
from openerp import tools

class Forum(models.Model):
    _inherit = "forum.forum"

    #Allow chrome extension link in forum
    allow_chrome_extension = fields.Boolean("Allo Chrome Extension")

    @api.depends('allow_chrome_extension')
    def _onchange_allow_chrome(self):
        self.allow_link = True

    @api.multi
    def generate_extension(self):
        with openerp.tools.osutil.tempdir() as ext_dir:
            #TODO: Get current directory instead of puttin static path
            source_path = os.path.abspath('addons/website_forum_chrome/forum_link_extension')
            ext_dir_path = os.path.join(ext_dir, 'forum_link_extension')
            shutil.copytree(source_path, ext_dir_path)
            config_file = open(ext_dir_path+'/static/src/js/config.js', 'wb')
            config_data = {
                'host': 'HOST',
                'database': 'DATABASE',
                'forum_name': 'FORUM NAME'
            }
            config_file.write(tools.ustr(config_data))
            config_file.close()
            t = tempfile.TemporaryFile()
            openerp.tools.osutil.zip_dir(ext_dir, t, include_dir=False)
            t.seek(0)
            return t
