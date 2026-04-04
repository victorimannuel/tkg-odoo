from odoo import models, fields


class GymMemberTag(models.Model):
    _name = 'gym.member.tag'
    _description = 'Member Tag'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color')
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
