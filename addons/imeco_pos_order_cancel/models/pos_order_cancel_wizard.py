from odoo import fields, models, _
from odoo.exceptions import UserError


class PosOrderCancelWizard(models.TransientModel):
    _name = 'pos.order.cancel.wizard'
    _description = 'POS Order Cancel Wizard'

    order_id = fields.Many2one(
        'pos.order',
        string='Order',
        required=True,
        readonly=True,
    )
    order_ref = fields.Char(
        related='order_id.pos_reference',
        string='Receipt Number',
        readonly=True,
    )
    amount_total = fields.Monetary(
        related='order_id.amount_total',
        string='Total Amount',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id',
        readonly=True,
    )
    session_state = fields.Selection(
        related='order_id.session_id.state',
        string='Session State',
        readonly=True,
    )
    cancel_reason = fields.Text(
        string='Cancellation Reason',
        required=True,
    )

    def action_confirm_cancel(self):
        """Called when the manager clicks Confirm in the wizard."""
        self.ensure_one()
        if not self.cancel_reason or not self.cancel_reason.strip():
            raise UserError(_('A cancellation reason is required.'))

        self.order_id.action_force_cancel_backend_clean(
            self.order_id.id,
            self.cancel_reason.strip(),
        )
        return {'type': 'ir.actions.act_window_close'}
