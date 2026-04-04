from random import randint

from odoo import models, fields


class GymRoom(models.Model):
    _name = 'gym.room'
    _description = 'Gym Room / Facility'

    name = fields.Char(required=True)
    capacity = fields.Integer(string='Capacity', default=10)
    equipment_notes = fields.Text(string='Equipment')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color', default=lambda self: randint(1, 11))
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Hours')
