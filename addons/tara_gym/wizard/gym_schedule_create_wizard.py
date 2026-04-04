from odoo import models, fields, api, _


class GymScheduleCreateWizard(models.TransientModel):
    _name = 'gym.schedule.create.wizard'
    _description = 'Schedule Create Wizard'

    start_datetime = fields.Datetime(string='Start Time')
    end_datetime = fields.Datetime(string='End Time')
    room_id = fields.Many2one('gym.room', string='Room')

    def action_create_class(self):
        return {
            'name': _('Create Class Session'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.class.session',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_start_datetime': self.start_datetime,
                'default_end_datetime': self.end_datetime,
                'default_room_id': self.room_id.id,
            }
        }

    def action_create_service(self):
        return {
            'name': _('Create Service Booking'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.service.booking',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_start_datetime': self.start_datetime,
                'default_end_datetime': self.end_datetime,
                'default_room_id': self.room_id.id,
            }
        }

