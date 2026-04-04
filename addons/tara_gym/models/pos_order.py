from odoo import models, fields, api, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

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

            # 1. Confirm draft subscriptions ONLY IF the purchased product matches the subscription's membership product
            # OR if a class product was purchased
            draft_subs = member.subscription_ids.filtered(lambda s: s.state == 'draft')
            for sub in draft_subs:
                if sub.membership_id.product_id.id in purchased_product_ids or any(p in purchased_product_ids for p in class_product_ids):
                    sub.action_confirm()

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
