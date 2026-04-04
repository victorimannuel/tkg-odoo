from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    gymmaster_product_id = fields.Char(string="GymMaster Product ID", index=True)
