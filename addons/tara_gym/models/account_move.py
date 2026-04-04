from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    gym_subscription_id = fields.Many2one('gym.membership.subscription', string='Gym Subscription')
