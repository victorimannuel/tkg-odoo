from odoo import models, fields

class GymMemberDocument(models.Model):
    _name = 'gym.member.document'
    _description = 'Member Documents'

    member_id = fields.Many2one('gym.member', string='Member', required=True, ondelete='cascade')
    name = fields.Char(string='Document Name', required=True)
    file = fields.Binary(string='File', attachment=True)
    expiry_date = fields.Date(string='Expiry Date')
    type = fields.Selection([
        ('waiver', 'Waiver'),
        ('id', 'ID Proof'),
        ('medical', 'Medical Certificate'),
        ('contract', 'Contract'),
        ('other', 'Other')
    ], string='Document Type', required=True)
