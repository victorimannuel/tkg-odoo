from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    gym_category_type = fields.Selection([
        ('membership', 'Membership'),
        ('class', 'Class'),
        ('service', 'Service'),
        ('other', 'Other'),
    ], string='Gym Category Type', default='other')
    
    active = fields.Boolean(default=True)
