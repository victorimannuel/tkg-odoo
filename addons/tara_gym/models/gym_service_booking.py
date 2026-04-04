from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class GymServiceBooking(models.Model):
    _name = 'gym.service.booking'
    _description = 'Service Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    service_id = fields.Many2one('gym.service', string='Service', required=True)
    member_id = fields.Many2one('gym.member', string='Member', required=True)
    trainer_id = fields.Many2one('gym.trainer', string='Trainer')
    room_id = fields.Many2one('gym.room', string='Room')

    start_datetime = fields.Datetime(string='Start', required=True)
    end_datetime = fields.Datetime(string='End', required=True)

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('canceled', 'Canceled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )

    price = fields.Float(string='Price')

    @api.depends('service_id', 'member_id', 'start_datetime')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.service_id:
                parts.append(rec.service_id.name)
            if rec.member_id:
                parts.append(rec.member_id.name)
            if rec.start_datetime:
                parts.append(fields.Datetime.to_string(rec.start_datetime))
            rec.name = " - ".join(parts) if parts else _('New')

    @api.onchange('service_id')
    def _onchange_service_id(self):
        for rec in self:
            if rec.service_id:
                rec.price = rec.service_id.price
                if rec.start_datetime and rec.service_id.duration_hours:
                    rec.end_datetime = rec.start_datetime + relativedelta(hours=rec.service_id.duration_hours)

    @api.onchange('start_datetime')
    def _onchange_start_datetime(self):
        for rec in self:
            if rec.service_id and rec.start_datetime and rec.service_id.duration_hours:
                rec.end_datetime = rec.start_datetime + relativedelta(hours=rec.service_id.duration_hours)

    @api.constrains('start_datetime', 'end_datetime')
    def _check_datetimes(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.start_datetime >= rec.end_datetime:
                raise ValueError(_("End datetime must be after start datetime"))

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for rec in self:
            self.env['gym.membership.benefit.usage'].recompute_for_member(rec.member_id)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'canceled'})
        for rec in self:
            self.env['gym.membership.benefit.usage'].recompute_for_member(rec.member_id)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.state not in ['draft', 'canceled']:
                self.env['gym.membership.benefit.usage'].recompute_for_member(rec.member_id)
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals or 'start_datetime' in vals or 'member_id' in vals:
            for rec in self:
                self.env['gym.membership.benefit.usage'].recompute_for_member(rec.member_id)
        return res
