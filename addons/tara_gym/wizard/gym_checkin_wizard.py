from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GymCheckinWizard(models.TransientModel):
    _name = 'gym.checkin.wizard'
    _description = 'Gym Check-in Wizard'

    member_id = fields.Many2one('gym.member', string='Member', required=True)
    subscription_id = fields.Many2one(
        'gym.membership.subscription', 
        string='Active Membership', 
        compute='_compute_subscription_id',
        store=True,
    )
    membership_name = fields.Char(related='subscription_id.membership_id.name', string='Membership Plan', readonly=True)
    door_id = fields.Many2one('gym.door', string='Door', domain="[('active', '=', True)]")
    method = fields.Selection([
        ('manual', 'Manual'),
        ('qr', 'QR Code'),
        ('rfid', 'RFID'),
        ('face', 'Face ID')
    ], string='Check-in Method', default='manual', required=True)

    @api.depends('member_id')
    def _compute_subscription_id(self):
        for rec in self:
            if rec.member_id:
                active_subs = rec.member_id.subscription_ids.filtered(lambda s: s.state == 'running')
                rec.subscription_id = active_subs.sorted(key=lambda s: s.date_start or s.create_date)[-1] if active_subs else False
            else:
                rec.subscription_id = False

    def action_confirm(self):
        self.ensure_one()
        
        # Validate door benefit only if subscription exists
        if self.subscription_id:
            door_benefits = self.subscription_id.membership_id.benefit_ids.filtered(lambda b: b.access_to == 'door')
            if not door_benefits:
                raise UserError(_("Membership '%s' does not include door access benefits.") % self.subscription_id.membership_id.name)
        
        # Create visitor record
        vals = {
            'member_id': self.member_id.id,
            'door_id': self.door_id.id if self.door_id else False,
            'method': self.method,
        }
        if self.subscription_id:
            vals['subscription_id'] = self.subscription_id.id
        self.env['gym.visitor'].create(vals)
        
        self.member_id.is_checked_in = True
        if self.subscription_id:
            self.member_id.action_refresh_benefits()
        return {'type': 'ir.actions.act_window_close'}
