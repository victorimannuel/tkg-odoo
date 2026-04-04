from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class GymMembershipSubscriptionFreeze(models.Model):
    _name = 'gym.membership.subscription.freeze'
    _description = 'Subscription Freeze'

    subscription_id = fields.Many2one('gym.membership.subscription', required=True)
    date_start = fields.Date(string='Freeze Start', required=True)
    date_end = fields.Date(string='Freeze End', required=True)
    reason = fields.Char(string='Reason')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start > record.date_end:
                raise ValidationError("Start date must be before end date")

    def action_apply(self):
        for freeze in self:
            if freeze.subscription_id.state != 'running':
                raise ValidationError("Only running subscriptions can be frozen")

            days = (freeze.date_end - freeze.date_start).days
            if freeze.subscription_id.date_end:
                freeze.subscription_id.date_end += relativedelta(days=days)

            freeze.subscription_id.write({'state': 'frozen'})
