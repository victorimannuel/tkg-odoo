from odoo import models, fields, api, _

class GymMemberHealth(models.Model):
    _name = 'gym.member.health'
    _description = 'Member Health Profile'
    _order = 'date desc'

    member_id = fields.Many2one('gym.member', string='Member', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today, required=True)
    height = fields.Float(string='Height (cm)')
    weight = fields.Float(string='Weight (kg)')
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True)
    fat_percentage = fields.Float(string='Body Fat %')
    muscle_mass = fields.Float(string='Muscle Mass (kg)')
    notes = fields.Text(string='Notes/Injuries')
    goals = fields.Text(string='Fitness Goals')

    @api.depends('height', 'weight')
    def _compute_bmi(self):
        for record in self:
            if record.height and record.weight:
                height_m = record.height / 100
                record.bmi = record.weight / (height_m ** 2)
            else:
                record.bmi = 0.0
