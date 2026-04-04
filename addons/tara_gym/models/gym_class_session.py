from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GymClassSession(models.Model):
    _name = 'gym.class.session'
    _description = 'Class Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(compute='_compute_name', store=True)
    class_id = fields.Many2one('gym.class', string='Class', required=True)
    trainer_id = fields.Many2one('gym.trainer', string='Trainer')
    room_id = fields.Many2one('gym.room', string='Room')
    room_color = fields.Integer(related='room_id.color', string='Room Color')
    
    start_datetime = fields.Datetime(string='Start Time', required=True)
    end_datetime = fields.Datetime(string='End Time', required=True)
    
    capacity = fields.Integer(string='Capacity')
    enrollment_ids = fields.One2many('gym.class.enrollment', 'session_id', string='Enrollments')
    enrollment_count = fields.Integer(compute='_compute_enrollment_count')
    
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('active', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    ], default='scheduled', tracking=True)

    @api.depends('class_id', 'start_datetime')
    def _compute_name(self):
        for record in self:
            if not record.class_id or not record.start_datetime:
                record.name = record.class_id.name if record.class_id else ''
                continue
            
            # Format: 24 Feb 2026
            date_str = record.start_datetime.strftime('%d %b %Y')
            # Format: 08:00
            time_str = record.start_datetime.strftime('%H:%M')
            
            record.name = f"{record.class_id.name} - {date_str}"

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            self.capacity = self.class_id.capacity

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for record in self:
            record.enrollment_count = len(record.enrollment_ids)

    @api.constrains('room_id', 'start_datetime', 'end_datetime')
    def _check_room_overlap(self):
        for record in self:
            if record.room_id:
                overlaps = self.search([
                    ('id', '!=', record.id),
                    ('room_id', '=', record.room_id.id),
                    ('start_datetime', '<', record.end_datetime),
                    ('end_datetime', '>', record.start_datetime),
                    ('state', '!=', 'canceled')
                ])
                if overlaps:
                    raise ValidationError(f"Room {record.room_id.name} is already booked for this time slot.")

    def action_add_enrollment(self):
        self.ensure_one()
        return {
            'name': _('Add Enrollment'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.class.enrollment.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
            }
        }

