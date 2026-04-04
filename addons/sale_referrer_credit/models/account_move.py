from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    referrer_partner_id = fields.Many2one('res.partner', string='Referrer', readonly=True, states={'draft': [('readonly', False)]})
    referrer_credit_entry_ids = fields.One2many('referrer.credit.ledger', 'source_invoice_id', string='Referrer Credits')

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        # We don't grant credit on post, but on payment.
        # However, requirements say: "Credits are ONLY granted when the related customer invoice is fully PAID."
        return res

    def _get_referrer_commission_percentage(self):
        # Allow extensibility
        return float(self.env['ir.config_parameter'].sudo().get_param('sale_referrer_credit.commission_percentage', default=5.0))

    def write(self, vals):
        res = super().write(vals)
        if 'matched_payment_ids' in vals:
            print(vals.get('matched_payment_ids'))
            self._check_grant_referrer_credit()
        return res

    def _check_grant_referrer_credit(self):
        # Get Config
        ICP = self.env['ir.config_parameter'].sudo()
        journal_id = int(ICP.get_param('sale_referrer_credit.referrer_journal_id') or 0)
        expense_account_id = int(ICP.get_param('sale_referrer_credit.referrer_expense_account_id') or 0)
        liability_account_id = int(ICP.get_param('sale_referrer_credit.referrer_liability_account_id') or 0)

        for move in self:
            if move.move_type == 'out_invoice' and move.referrer_partner_id and move.payment_state == 'paid':
                # Check if we already granted credit for this invoice
                existing_credit = self.env['referrer.credit.ledger'].search([
                    ('source_invoice_id', '=', move.id),
                    ('credit_type', '=', 'earn')
                ])
                if not existing_credit:
                    percentage = move._get_referrer_commission_percentage()
                    amount = move.amount_untaxed * (percentage / 100.0)
                    
                    if amount > 0:
                        # Create Accounting Entry if configured
                        move_id = False
                        if journal_id and expense_account_id and liability_account_id:
                             move_vals = {
                                 'journal_id': journal_id,
                                 'date': fields.Date.today(),
                                 'ref': _('Referrer Commission: %s') % move.name,
                                 'move_type': 'entry',
                                 'line_ids': [
                                     (0, 0, {
                                         'name': _('Commission Expense'),
                                         'account_id': expense_account_id,
                                         'debit': amount,
                                         'credit': 0.0,
                                     }),
                                     (0, 0, {
                                         'name': _('Commission Payable to %s') % move.referrer_partner_id.name,
                                         'account_id': liability_account_id,
                                         'partner_id': move.referrer_partner_id.id,
                                         'debit': 0.0,
                                         'credit': amount,
                                     }),
                                 ]
                             }
                             ac_move = self.env['account.move'].create(move_vals)
                             ac_move.action_post()
                             move_id = ac_move.id

                        self.env['referrer.credit.ledger'].create({
                            'partner_id': move.referrer_partner_id.id,
                            'source_invoice_id': move.id,
                            'sale_order_id': move.invoice_line_ids.mapped('sale_line_ids.order_id')[:1].id if move.invoice_line_ids.mapped('sale_line_ids') else False,
                            'credit_amount': amount,
                            'credit_type': 'earn',
                            'state': 'posted',
                            'account_move_id': move_id,
                        })
            
            # Handle Refunds/Credit Notes
            if move.move_type == 'out_refund' and move.referrer_partner_id and move.payment_state == 'paid':
                 # Check if we already processed this refund
                existing_adjustment = self.env['referrer.credit.ledger'].search([
                    ('source_invoice_id', '=', move.id),
                    ('credit_type', '=', 'adjustment')
                ])
                if not existing_adjustment:
                    percentage = move._get_referrer_commission_percentage()
                    amount = move.amount_untaxed * (percentage / 100.0)
                    
                    if amount > 0:
                        # Create Accounting Entry for Adjustment (Reverse)
                        move_id = False
                        if journal_id and expense_account_id and liability_account_id:
                             move_vals = {
                                 'journal_id': journal_id,
                                 'date': fields.Date.today(),
                                 'ref': _('Referrer Commission Adjustment: %s') % move.name,
                                 'move_type': 'entry',
                                 'line_ids': [
                                     (0, 0, {
                                         'name': _('Commission Expense Reversal'),
                                         'account_id': expense_account_id,
                                         'debit': 0.0,
                                         'credit': amount,
                                     }),
                                     (0, 0, {
                                         'name': _('Commission Payable Reversal'),
                                         'account_id': liability_account_id,
                                         'partner_id': move.referrer_partner_id.id,
                                         'debit': amount,
                                         'credit': 0.0,
                                     }),
                                 ]
                             }
                             ac_move = self.env['account.move'].create(move_vals)
                             ac_move.action_post()
                             move_id = ac_move.id

                         # Refund reduces the credit, so we create a negative adjustment
                         # amount_untaxed on refund is positive, so we negate it
                        self.env['referrer.credit.ledger'].create({
                            'partner_id': move.referrer_partner_id.id,
                            'source_invoice_id': move.id,
                            'sale_order_id': move.reversed_entry_id.invoice_line_ids.mapped('sale_line_ids.order_id')[:1].id if move.reversed_entry_id else False,
                            'credit_amount': -amount,
                            'credit_type': 'adjustment',
                            'state': 'posted',
                            'account_move_id': move_id,
                        })
