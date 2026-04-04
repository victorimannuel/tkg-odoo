import logging

from odoo import models, fields


_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _auto_pay_subscription_invoice_from_pos(self, sub, order):
        """Post and pay newly created subscription invoice using POS payment journal."""
        invoice = sub.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]
        if not invoice:
            return

        invoice.action_post()

        if invoice.amount_residual <= 0:
            return

        payment_journal = False
        if order.payment_ids:
            payment_journal = order.payment_ids[0].payment_method_id.journal_id
        if not payment_journal and getattr(order, 'session_id', False):
            payment_journal = order.session_id.config_id.journal_id
        if not payment_journal:
            _logger.warning(
                "Cannot auto-pay invoice %s for subscription %s: no payment journal found from POS order %s.",
                invoice.name, sub.name, order.name
            )
            return

        register_ctx = {
            'active_model': 'account.move',
            'active_ids': invoice.ids,
        }
        register_vals = {
            'journal_id': payment_journal.id,
            'amount': invoice.amount_residual,
            'payment_date': fields.Date.context_today(self),
        }
        register = self.env['account.payment.register'].with_context(register_ctx).create(register_vals)
        register.action_create_payments()

    def _confirm_and_settle_subscriptions_from_order(self, member, order, purchased_product_ids, class_product_ids):
        """Confirm relevant draft subscriptions and settle their invoices from POS payment."""
        draft_subs = member.subscription_ids.filtered(lambda s: s.state == 'draft')
        if not draft_subs:
            return

        # Regular membership flow: match subscription by purchased membership product.
        matching_subs = draft_subs.filtered(
            lambda s: s.membership_id.product_id.id in purchased_product_ids
        )

        # Class enrollment paid via POS: confirm only configured class drop-in membership.
        class_drop_in_id = int(
            self.env['ir.config_parameter'].sudo().get_param('tara_gym.default_drop_in_membership_id', '0')
        )
        purchased_class = any(p in purchased_product_ids for p in class_product_ids)
        if purchased_class and class_drop_in_id:
            class_drop_in_subs = draft_subs.filtered(lambda s: s.membership_id.id == class_drop_in_id)
            matching_subs |= class_drop_in_subs

        for sub in matching_subs:
            sub.action_confirm()
            self._auto_pay_subscription_invoice_from_pos(sub, order)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        
        drop_in_membership_id = int(self.env['ir.config_parameter'].sudo().get_param('tara_gym.default_drop_in_visit_membership_id', 0))
        drop_in_membership = self.env['gym.membership'].browse(drop_in_membership_id)
        drop_in_product_id = drop_in_membership.product_id.id if drop_in_membership else False

        for order in self:
            if not order.partner_id:
                continue
            
            member = self.env['gym.member'].search(
                [('partner_id', '=', order.partner_id.id)], limit=1
            )
            if not member:
                continue

            # Check products bought in this specific order
            purchased_product_ids = order.lines.mapped('product_id.id')
            
            # Get all class products to check if a class was purchased (for drop-in class enrollments)
            class_product_ids = self.env['gym.class'].search([]).mapped('product_id.id')

            # 1. Confirm and settle relevant draft subscriptions for this order.
            self._confirm_and_settle_subscriptions_from_order(
                member=member,
                order=order,
                purchased_product_ids=purchased_product_ids,
                class_product_ids=class_product_ids,
            )

            # 1.5 Confirm draft class enrollments if a class product was purchased
            if any(p in purchased_product_ids for p in class_product_ids):
                draft_enrollments = self.env['gym.class.enrollment'].search([
                    ('member_id', '=', member.id),
                    ('state', '=', 'draft')
                ])
                for enrollment in draft_enrollments:
                    enrollment.state = 'confirmed'

            # 2. Auto check-in ONLY IF they bought the drop-in pass in this order
            if drop_in_product_id and drop_in_product_id in purchased_product_ids:
                if not member.is_checked_in:
                    member.is_checked_in = True
                    self.env['gym.visitor'].create({
                        'member_id': member.id,
                        'method': 'manual',
                    })
                    
        return res
