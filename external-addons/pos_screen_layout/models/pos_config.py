from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    swap_panes = fields.Boolean(
        string='Swap Left/Right Panes',
        default=False,
        help='Move the product grid and payment controls to the opposite side of the screen.',
    )
