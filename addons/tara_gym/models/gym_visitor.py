from odoo import models, fields, api, _


class GymVisitor(models.Model):
    _name = 'gym.visitor'
    _description = 'Gym Visit / Check-in'
    _order = 'checkin_time desc'

    member_id = fields.Many2one('gym.member', string='Member', required=True, ondelete='cascade')
    subscription_id = fields.Many2one('gym.membership.subscription', string='Membership Subscription')
    door_id = fields.Many2one('gym.door', string='Door')
    session_id = fields.Many2one('gym.class.session', string='Class Session')
    checkin_time = fields.Datetime(string='Check-in Time', default=fields.Datetime.now, required=True)
    checkout_time = fields.Datetime(string='Check-out Time')

    method = fields.Selection([
        ('manual', 'Manual'),
        ('qr', 'QR Code'),
        ('rfid', 'RFID'),
        ('face', 'Face ID')
    ], string='Check-in Method', default='manual')

    status = fields.Selection([
        ('active', 'Inside'),
        ('completed', 'Checked Out')
    ], string='Status', default='active', compute='_compute_status', store=True)

    @api.depends('checkout_time')
    def _compute_status(self):
        for record in self:
            record.status = 'completed' if record.checkout_time else 'active'
