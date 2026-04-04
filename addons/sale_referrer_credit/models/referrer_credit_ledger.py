from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ReferrerCreditLedger(models.Model):
    _name = 'referrer.credit.ledger'
    _description = 'Referrer Credit Ledger'
    _order = 'create_date desc, id desc'

    partner_id = fields.Many2one('res.partner', string='Referrer', required=True, index=True, readonly=True)
    source_invoice_id = fields.Many2one('account.move', string='Source Invoice', readonly=True, help="Invoice that generated this credit")
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    account_move_id = fields.Many2one('account.move', string='Accounting Entry', readonly=True, help="Journal Entry created for this credit.")
    credit_amount = fields.Float(string='Amount', required=True, readonly=True, digits='Account')
    credit_type = fields.Selection([
        ('earn', 'Earned'),
        ('redeem', 'Redeemed'),
        ('adjustment', 'Adjustment')
    ], string='Type', required=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='posted', required=True, readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'credit_amount' in vals and vals['credit_type'] == 'redeem' and vals['credit_amount'] > 0:
                 # Redeeming credits should usually be a negative amount in the ledger to reduce balance, 
                 # or we store positive and subtract. Let's stick to signed amounts for easier summing.
                 # User requirements say "Credits accumulate...".
                 # Standard accounting: Credits (Liability/Payable to partner) are positive. Redemptions are negative.
                 pass
        return super().create(vals_list)

    def unlink(self):
        raise ValidationError(_("You cannot delete ledger entries. Create an adjustment entry instead."))

