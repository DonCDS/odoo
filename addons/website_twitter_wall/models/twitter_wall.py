from openerp import fields, models


class TwitterWall(models.Model):
    _inherit = "stream.agent"

    description = fields.Text('Wall Description')
    website_id = fields.Many2one('website', 'Website')
    user_id = fields.Many2one('res.users', 'Created User')
    number_view = fields.Integer('# of Views')
    website_published = fields.Boolean('Visible in Website')
    image = fields.Binary('Image')
    m2o_col = fields.Char('Stream Id', default="wall_id")

    def create(self, values):
        stream_id = self.env['twitter.stream'].search([('model', '=', 'stream.agent')], limit=1)
        values.update({'stream_id': stream_id.id})
        super(TwitterWall, self).create(values)
