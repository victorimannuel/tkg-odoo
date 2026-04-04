from odoo import models, fields, api, _


class GymService(models.Model):
    _name = 'gym.service'
    _description = 'Gym Service'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    product_id = fields.Many2one(
        'product.product',
        string='Linked Product',
        domain=[('type', '=', 'service')]
    )
    category_id = fields.Many2one(
        'product.category', 
        related='product_id.categ_id', 
        readonly=False, 
        store=True,
        string='Category',
        domain=[('gym_category_type', '=', 'service'), ('active', '=', True)]
    )
    service_type = fields.Selection(
        [
            ('pt', 'Personal Training'),
            ('room', 'Room Booking'),
            ('other', 'Other Service'),
        ],
        string='Service Type',
        required=True,
        default='pt',
    )
    duration_hours = fields.Float(string='Duration (Hours)', default=1.0)
    price = fields.Float(string='Price', related='product_id.list_price', readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_id'):
                product_vals = {
                    'name': vals.get('name') or _('New Service'),
                    'type': 'service',
                    'list_price': vals.get('price') or 0.0,
                    'taxes_id': False,
                    'supplier_taxes_id': False,
                }
                if vals.get('category_id'):
                    product_vals['categ_id'] = vals.get('category_id')
                product = self.env['product.product'].create(product_vals)
                vals['product_id'] = product.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for rec in self:
                if rec.product_id:
                    rec.product_id.name = vals['name']
        return res
