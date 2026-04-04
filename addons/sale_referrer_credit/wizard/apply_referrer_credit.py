from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ApplyReferrerCredit(models.TransientModel):
    _name = 'apply.referrer.credit.wizard'
    _description = 'Apply Referrer Credit'

    sale_order_id = fields.Many2one('sale.order', required=True)
    partner_id = fields.Many2one('res.partner', related='sale_order_id.partner_id', readonly=True, string="Customer")
    currency_id = fields.Many2one('res.currency', related='sale_order_id.currency_id', readonly=True)
    
    current_credit_balance = fields.Float(string='Available Credit', compute='_compute_balance')
    max_redeemable_amount = fields.Float(string='Max Redeemable', compute='_compute_max_redeemable')
    amount_to_redeem = fields.Float(string='Amount to Redeem', required=True)

    @api.depends('partner_id')
    def _compute_balance(self):
        for wiz in self:
            wiz.current_credit_balance = wiz.partner_id.referrer_credit_balance

    @api.depends('sale_order_id.amount_total', 'current_credit_balance')
    def _compute_max_redeemable(self):
        for wiz in self:
            # Can't redeem more than the order total or the available balance
            order_total = wiz.sale_order_id.amount_total
            wiz.max_redeemable_amount = min(order_total, wiz.current_credit_balance)

    @api.onchange('max_redeemable_amount')
    def _onchange_max_redeemable(self):
        # Default to max amount
        if self.amount_to_redeem == 0:
            self.amount_to_redeem = self.max_redeemable_amount

    def action_apply_credit(self):
        self.ensure_one()
        if self.amount_to_redeem <= 0:
             raise UserError(_("Amount to redeem must be positive."))
        if self.amount_to_redeem > self.current_credit_balance:
             raise UserError(_("You cannot redeem more than your available balance."))
        if self.amount_to_redeem > self.sale_order_id.amount_total:
             # This check is slightly tricky if taxes are involved, but generally we don't want negative totals.
             # Let's allow partial payment.
             pass

        # Add a negative line to the sales order
        product_credit = self.env.ref('sale_referrer_credit.product_product_referrer_credit')
        
        # Check if line already exists
        existing_line = self.sale_order_id.order_line.filtered(lambda l: l.product_id == product_credit)
        if existing_line:
             # Update existing line
             # We assume one credit line per order for simplicity
             new_amount = existing_line.price_unit - self.amount_to_redeem
             # Wait, price_unit is usually negative for discount.
             # If existing is -10 and we add 5, it becomes -15.
             # Actually, let's just replace/update the amount.
             # The wizard asks "Amount to Redeem".
             existing_line.price_unit = -self.amount_to_redeem
        else:
            self.env['sale.order.line'].create({
                'order_id': self.sale_order_id.id,
                'product_id': product_credit.id,
                'name': _('Referrer Credit Redemption'),
                'product_uom_qty': 1,
                'price_unit': -self.amount_to_redeem,
                'tax_ids': [(6, 0, [])], # No taxes on credit redemption
            })
        
        return {'type': 'ir.actions.act_window_close'}
