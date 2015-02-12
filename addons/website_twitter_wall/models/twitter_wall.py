from openerp import fields, models


class TwitterWall(models.Model):
    _inherit = "stream.agent"

    name = fields.Char('Name')
    description = fields.Text('Wall Description')
    user_id = fields.Many2one('res.users', 'User Id')
    number_view = fields.Integer('# of Views')
    website_published = fields.Boolean('Visible in Website')
    image = fields.Binary('Image')

    def create(self, values):
        stream_id = self.env['twitter.stream'].search([('model', '=', 'stream.agent')], limit=1)
        values.update({'stream_id': stream_id.id})
        super(TwitterWall, self).create(values)
