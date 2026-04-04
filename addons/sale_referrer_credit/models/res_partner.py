from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    referrer_credit_balance = fields.Float(string='Referrer Credit Balance', compute='_compute_referrer_credit_balance', digits='Account')
    referrer_ledger_ids = fields.One2many('referrer.credit.ledger', 'partner_id', string='Referrer Ledger Entries')

    @api.depends('referrer_ledger_ids.credit_amount', 'referrer_ledger_ids.state')
    def _compute_referrer_credit_balance(self):
        for partner in self:
            balance = sum(partner.referrer_ledger_ids.filtered(lambda l: l.state == 'posted').mapped('credit_amount'))
            partner.referrer_credit_balance = balance

    def action_view_referrer_ledger(self):
        self.ensure_one()
        return {
            'name': 'Referrer Credits',
            'type': 'ir.actions.act_window',
            'res_model': 'referrer.credit.ledger',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
