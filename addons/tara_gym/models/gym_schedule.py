from odoo import models, fields, api, tools, _

class GymSchedule(models.Model):
    _name = 'gym.schedule'
    _description = 'Gym Master Schedule'
    _auto = False
    _order = 'start_datetime desc'

    name = fields.Char(string='Event', readonly=True)
    start_datetime = fields.Datetime(string='Start Time', readonly=True)
    end_datetime = fields.Datetime(string='End Time', readonly=True)
    trainer_id = fields.Many2one('gym.trainer', string='Trainer', readonly=True)
    room_id = fields.Many2one('gym.room', string='Room', readonly=True)
    room_color = fields.Integer(string='Room Color', readonly=True)
    booking_type = fields.Selection([
        ('class', 'Class Session'),
        ('service', 'Service Booking')
    ], string='Type', readonly=True)
    res_model = fields.Char(string='Resource Model', readonly=True)
    res_id = fields.Integer(string='Resource ID', readonly=True)
    
    res_reference = fields.Reference(selection=[
        ('gym.class.session', 'Class Session'),
        ('gym.service.booking', 'Service Booking')
    ], string='Source Record', readonly=True)
    
    state = fields.Char(string='Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    (s.id * 2) AS id,
                    s.name AS name,
                    s.start_datetime AS start_datetime,
                    s.end_datetime AS end_datetime,
                    s.trainer_id AS trainer_id,
                    s.room_id AS room_id,
                    r.color AS room_color,
                    'class' AS booking_type,
                    'gym.class.session' AS res_model,
                    s.id AS res_id,
                    'gym.class.session,' || s.id AS res_reference,
                    s.state AS state
                FROM gym_class_session s
                LEFT JOIN gym_room r ON s.room_id = r.id
                WHERE s.state != 'canceled'
                
                UNION ALL
                
                SELECT 
                    (b.id * 2 + 1) AS id,
                    b.name AS name,
                    b.start_datetime AS start_datetime,
                    b.end_datetime AS end_datetime,
                    b.trainer_id AS trainer_id,
                    b.room_id AS room_id,
                    r.color AS room_color,
                    'service' AS booking_type,
                    'gym.service.booking' AS res_model,
                    b.id AS res_id,
                    'gym.service.booking,' || b.id AS res_reference,
                    b.state AS state
                FROM gym_service_booking b
                LEFT JOIN gym_room r ON b.room_id = r.id
                WHERE b.state != 'canceled'
            )
        """ % self._table)

    @api.model
    def create(self, vals):
        # gym.schedule is a read-only SQL UNION view — cannot be written to.
        # Redirect to the create wizard which lets the user choose class or service.
        from odoo.exceptions import RedirectWarning

        if isinstance(vals, list):
            vals = vals[0] if vals else {}

        action = {
            'name': _('Create New Event'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.schedule.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_start_datetime': vals.get('start_datetime'),
                'default_end_datetime': vals.get('end_datetime'),
            }
        }
        raise RedirectWarning(_('Choose what type of event to create.'), action, _('Continue'))

    def action_open_record(self):
        self.ensure_one()
        return {
            'name': _('Edit %s') % (self.name),
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
            'context': self.env.context,
        }

    def action_create_class(self):
        return {
            'name': _('Create Class Session'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.class.session',
            'view_mode': 'form',
            # include at least one view entry so _preprocessAction can map over it
            'views': [[False, 'form']],
            'target': 'current',
            'context': {
                'default_start_datetime': self.start_datetime or self.env.context.get('default_start_datetime'),
                'default_end_datetime': self.end_datetime or self.env.context.get('default_end_datetime'),
            }
        }

    def action_create_service(self):
        return {
            'name': _('Create Service Booking'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.service.booking',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
            'context': {
                'default_start_datetime': self.start_datetime or self.env.context.get('default_start_datetime'),
                'default_end_datetime': self.end_datetime or self.env.context.get('default_end_datetime'),
            }
        }
