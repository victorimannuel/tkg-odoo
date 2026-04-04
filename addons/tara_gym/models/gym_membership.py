from odoo import models, fields, api, _

class GymMembership(models.Model):
    _name = 'gym.membership'
    _description = 'Membership'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    product_id = fields.Many2one('product.product', string='Linked Product', domain=[('type', '=', 'service')], ondelete='restrict')
    category_id = fields.Many2one(
        'product.category', 
        related='product_id.categ_id', 
        readonly=False, 
        store=True,
        string='Category',
        domain=[('gym_category_type', '=', 'membership'), ('active', '=', True)]
    )
    duration = fields.Integer(string='Duration', default=1, required=True)
    duration_uom = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Unit', default='months', required=True)
    payment_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('one_time', 'One Time')
    ], string='Payment Frequency', default='monthly', required=True)

    price = fields.Float(string='Price', related='product_id.list_price', readonly=False)
    basis = fields.Selection([
        ('renewal_based', 'Renewal Based Contract'),
    ], string='Membership Basis', default='renewal_based', required=True)

    session_count = fields.Integer(string='Included Sessions', help="For class-based/punch cards")
    usage_limit = fields.Integer(string='Usage Limit', default=0, help="Total usage limit across all benefits. 0 means unlimited.")
    allow_freeze = fields.Boolean(string='Allow Freezing', default=True)
    max_freeze_days = fields.Integer(string='Max Freeze Days', default=30)
    benefit_ids = fields.One2many('gym.membership.benefit', 'membership_id', string='Benefits')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_id'):
                product_vals = {
                    'name': vals.get('name') or _('New Membership'),
                    'type': 'service',
                    'list_price': vals.get('price') or 0.0,
                    'taxes_id': False,
                    'supplier_taxes_id': False,
                    'available_in_pos': True,
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
