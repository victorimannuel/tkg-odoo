from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    referrer_partner_id = fields.Many2one('res.partner', string='Referrer', help="Partner who referred this sale.")

    @api.constrains('referrer_partner_id', 'partner_id')
    def _check_referrer_not_customer(self):
        for order in self:
            if order.referrer_partner_id and order.referrer_partner_id == order.partner_id:
                raise ValidationError(_("The customer cannot be their own referrer."))

    def action_open_apply_credit_wizard(self):
        self.ensure_one()
        return {
            'name': 'Apply Credit',
            'type': 'ir.actions.act_window',
            'res_model': 'apply.referrer.credit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def action_confirm(self):
        # When order is confirmed, we need to DEDUCT the credit from the partner's ledger
        # IF there is a redemption line.
        res = super().action_confirm()
        for order in self:
            credit_product = self.env.ref('sale_referrer_credit.product_product_referrer_credit', raise_if_not_found=False)
            if not credit_product:
                continue
            
            # Find lines with this product
            # Note: price_unit should be negative
            redemption_lines = order.order_line.filtered(lambda l: l.product_id == credit_product and l.price_unit < 0)
            
            total_redemption = sum(abs(l.price_unit * l.product_uom_qty) for l in redemption_lines)
            
            if total_redemption > 0:
                # Check balance again just in case
                if order.partner_id.referrer_credit_balance < total_redemption:
                     raise ValidationError(_("Insufficient credit balance to confirm this order. Please adjust the credit amount."))

                # Create Ledger Entry
                self.env['referrer.credit.ledger'].create({
                    'partner_id': order.partner_id.id,
                    'sale_order_id': order.id,
                    'credit_amount': -total_redemption, # Negative for redemption
                    'credit_type': 'redeem',
                    'state': 'posted',
                })
        return res

    def action_cancel(self):
        # If order is cancelled, we should REFUND the credit back to the partner
        res = super().action_cancel()
        for order in self:
            # Find redemption entries linked to this order
            redemptions = self.env['referrer.credit.ledger'].search([
                ('sale_order_id', '=', order.id),
                ('credit_type', '=', 'redeem'),
                ('state', '=', 'posted')
            ])
            
            # Revert them
            for red in redemptions:
                 # Create a positive entry to reverse the redemption
                 self.env['referrer.credit.ledger'].create({
                    'partner_id': order.partner_id.id,
                    'sale_order_id': order.id,
                    'credit_amount': abs(red.credit_amount),
                    'credit_type': 'adjustment', # Or 'earn'? Adjustment is clearer for reversal
                    'state': 'posted',
                })
        return res

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.referrer_partner_id:
            invoice_vals['referrer_partner_id'] = self.referrer_partner_id.id
        return invoice_vals
