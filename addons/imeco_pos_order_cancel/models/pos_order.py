from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    cancel_reason_clean = fields.Text(string='Cancel Reason', readonly=True, copy=False)

    def action_open_cancel_wizard_clean(self):
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise AccessError(_('Only a POS manager can cancel orders from backend.'))
        if self.state not in ('paid', 'done'):
            raise UserError(_('Only paid or posted orders can be cancelled.'))
        if self.session_id.state == 'closed':
            raise UserError(_('Cannot cancel order from a closed session. Use refund instead.'))
        return {
            'name': _('Cancel POS Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'imeco.pos.order.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    @api.model
    def action_force_cancel_backend_clean(self, order_id, reason):
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise AccessError(_('Only a POS manager can cancel orders from backend.'))
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_('Order not found.'))
        if order.state not in ('paid', 'done'):
            raise UserError(_('Only paid or posted orders can be cancelled.'))
        if order.session_id.state == 'closed':
            raise UserError(_('Cannot cancel order from a closed session. Use refund instead.'))
        if not reason or not reason.strip():
            raise UserError(_('A cancellation reason is required.'))

        order.payment_ids.unlink()

        for picking in order.picking_ids:
            if picking.state == 'done':
                return_wizard = self.env['stock.return.picking'].with_context(
                    active_id=picking.id,
                    active_model='stock.picking',
                ).create({'picking_id': picking.id})
                for return_line in return_wizard.product_return_moves:
                    if return_line.move_id and return_line.move_id.state != 'cancel':
                        return_line.quantity = return_line.move_id.quantity
                return_picking = return_wizard._create_return()
                for move in return_picking.move_ids:
                    move.quantity = move.product_uom_qty
                return_picking.with_context(skip_backorder=True).button_validate()
            elif picking.state not in ('cancel',):
                picking.action_cancel()

        clean_reason = reason.strip()
        # Odoo 19 blocks write() from changing paid/done POS orders back to another
        # state, so we apply the final state switch through SQL after all reversals.
        self.env.cr.execute(
            """
            UPDATE pos_order
               SET state = %s,
                   cancel_reason_clean = %s,
                   write_uid = %s,
                   write_date = NOW()
             WHERE id = %s
            """,
            ('cancel', clean_reason, self.env.uid, order.id),
        )
        order.invalidate_recordset(['state', 'cancel_reason_clean'])
        order.message_post(body=_('Order cancelled from backend. Reason: %s', clean_reason))
        if order.session_id.state == 'opened':
            order.config_id.notify_synchronisation(order.session_id.id, self.env.context.get('device_identifier', 0))
        return True
