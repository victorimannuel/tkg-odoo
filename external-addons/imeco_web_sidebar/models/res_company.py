from odoo import models, fields


class ResCompany(models.Model):
    
    _inherit = 'res.company'
    
    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    sidebar_image = fields.Binary(
        string='Sidebar Image',
        attachment=True
    )
    
    background_image = fields.Binary(
        string='Apps Menu Background Image',
        attachment=True
    )