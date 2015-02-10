# -*- coding: utf-8 -*-

from openerp import api, fields, models


class hr_job(models.Model):
    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.mixin']

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(hr_job, self)._website_url(field_name, arg)
        for job in self:
            res[job.id] = "/jobs/detail/%s" % job.id
        return res

    @api.multi
    def job_open(self):
        self.write({'website_published': False})
        return super(hr_job, self).job_open()

    website_description = fields.Html('Website description')
