from odoo import models, fields, api, _


class GymClassEnrollment(models.Model):
    _name = 'gym.class.enrollment'
    _description = 'Class Enrollment'

    def _default_price(self):
        price = self.session_id.class_id.price
        print(self.session_id)
        if not self.membership_id:
            price = 0
        return price
    
    session_id = fields.Many2one('gym.class.session', required=True)
    start_datetime = fields.Datetime(related='session_id.start_datetime', string='Start Time', store=False)
    end_datetime = fields.Datetime(related='session_id.end_datetime', string='End Time', store=False)
    member_id = fields.Many2one('gym.member', required=True)
    membership_id = fields.Many2one(
        'gym.membership', 
        string='Membership', 
        compute='_compute_membership_id',
        store=True,
    )
    price = fields.Float(string='Price Paid', default=_default_price)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Registered'),
        ('waitlist', 'Waitlist'),
        ('canceled', 'Canceled'),
        ('attended', 'Attended'),
        ('no_show', 'No Show')
    ], default='draft')

    @api.depends('member_id')
    def _compute_membership_id(self):
        drop_in_id = int(self.env['ir.config_parameter'].sudo().get_param('tara_gym.default_drop_in_membership_id', '0'))
        drop_in = self.env['gym.membership'].browse(drop_in_id).exists() if drop_in_id else False
        for rec in self:
            if rec.member_id and rec.member_id.current_subscription_membership_id:
                rec.membership_id = rec.member_id.current_subscription_membership_id
            else:
                rec.membership_id = drop_in or False

    def action_checkin(self):
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'attended'
    
    _sql_constraints = [
        ('uniq_member_session', 'unique(session_id, member_id)', "Member already enrolled in this session")
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        Usage = self.env['gym.membership.benefit.usage']
        for rec in records:
            if rec.member_id:
                Usage.recompute_for_member(rec.member_id)
            
            # If created as attended, create visitor (skip if in import context)
            if rec.state == 'attended' and not self.env.context.get('skip_visitor_creation'):
                active_sub = self.env['gym.membership.subscription'].search([
                    ('member_id', '=', rec.member_id.id),
                    ('state', '=', 'running')
                ], limit=1)
                self.env['gym.visitor'].create({
                    'member_id': rec.member_id.id,
                    'subscription_id': active_sub.id if active_sub else False,
                    'session_id': rec.session_id.id,
                    'method': 'manual',
                    'checkin_time': fields.Datetime.now(),
                })
                rec.member_id.is_checked_in = True
        return records

    def write(self, vals):
        # Track state change to 'attended' (skip if in import context)
        if 'state' in vals and vals['state'] == 'attended' and not self.env.context.get('skip_visitor_creation'):
            for rec in self:
                if rec.state != 'attended':
                    # Find active subscription for this member
                    active_sub = self.env['gym.membership.subscription'].search([
                        ('member_id', '=', rec.member_id.id),
                        ('state', '=', 'running')
                    ], limit=1)
                    
                    # Create visitor record
                    self.env['gym.visitor'].create({
                        'member_id': rec.member_id.id,
                        'subscription_id': active_sub.id if active_sub else False,
                        'session_id': rec.session_id.id,
                        'method': 'manual',
                        'checkin_time': fields.Datetime.now(),
                    })
                    rec.member_id.is_checked_in = True

        res = super().write(vals)
        Usage = self.env['gym.membership.benefit.usage']
        for rec in self:
            if rec.member_id:
                Usage.recompute_for_member(rec.member_id)
        return res
