from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_swap_panes = fields.Boolean(
        related='pos_config_id.swap_panes',
        readonly=False,
    )
