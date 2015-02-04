from openerp import tools
from openerp.osv import osv
from openerp import addons

class AccountWizard_cd(osv.osv_memory):
	_inherit='wizard.multi.charts.accounts'
	
	_defaults = {
		'use_anglo_saxon': True,
	}