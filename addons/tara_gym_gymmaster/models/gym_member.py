from odoo import fields, models


class GymMember(models.Model):
    _inherit = "gym.member"

    gymmaster_member_id = fields.Char(string="GymMaster Member ID", index=True)


class GymMembership(models.Model):
    _inherit = "gym.membership"

    gymmaster_membership_id = fields.Char(string="GymMaster Membership ID", index=True)
