from odoo import models, fields

class GymDoor(models.Model):
    _name = 'gym.door'
    _description = 'Physical Door'

    name = fields.Char(required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)
