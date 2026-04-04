from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gym_drop_in_membership_id = fields.Many2one(
        'gym.membership',
        string='Default Drop-In Membership',
        config_parameter='tara_gym.default_drop_in_membership_id',
        help='Default membership assigned to class enrollments for members without an active subscription.',
    )

    gym_drop_in_visit_membership_id = fields.Many2one(
        'gym.membership',
        string='Drop-In Visit Membership',
        config_parameter='tara_gym.default_drop_in_visit_membership_id',
        help='Membership automatically assigned when registering a drop-in visitor.',
    )

    gym_pos_config_id = fields.Many2one(
        'pos.config',
        string='POS Config',
        config_parameter='tara_gym.gym_pos_config_id',
        help='Point of Sale configuration used for gym transactions (e.g. drop-in payments).',
    )
