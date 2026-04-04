from odoo import models, fields, api, _
from datetime import datetime, time

class GymMembershipBenefitUsage(models.Model):
    _name = 'gym.membership.benefit.usage'
    _description = 'Membership Benefit Usage'

    member_id = fields.Many2one('gym.member', string='Member', required=True, ondelete='cascade')
    subscription_id = fields.Many2one('gym.membership.subscription', string='Subscription', required=True, ondelete='cascade')
    membership_id = fields.Many2one('gym.membership', string='Membership', related='subscription_id.membership_id', store=True)
    benefit_id = fields.Many2one('gym.membership.benefit', string='Benefit', required=True, ondelete='cascade')
    benefit_name = fields.Char(string='Benefit', related='benefit_id.name', store=False)
    access_to = fields.Selection(related='benefit_id.access_to', store=False)
    usage_limit = fields.Integer(string='Usage Limit', related='membership_id.usage_limit', store=False)
    used_count = fields.Integer(string='Used')
    usage_display = fields.Char(string='Usage', compute='_compute_usage_display', store=False)

    @api.depends('used_count', 'usage_limit', 'access_to')
    def _compute_usage_display(self):
        for rec in self:
            if rec.access_to == 'door':
                rec.usage_display = "Unlimited"
                continue
            limit = rec.usage_limit or 0
            if limit:
                rec.usage_display = "%s/%s" % (rec.used_count, limit)
            else:
                rec.usage_display = "%s/∞" % rec.used_count

    @api.model
    def recompute_for_member(self, member):
        Subscription = self.env['gym.membership.subscription']
        Enrollment = self.env['gym.class.enrollment']
        today = fields.Date.context_today(self)

        self.search([('member_id', '=', member.id)]).unlink()

        subs = Subscription.search([
            ('member_id', '=', member.id),
            ('state', '=', 'running'),
        ])

        for sub in subs:
            if not sub.membership_id or not sub.membership_id.benefit_ids or not sub.date_start:
                continue
            start_date = sub.date_start
            end_date = sub.date_end or today
            if end_date < start_date:
                end_date = start_date
            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            for benefit in sub.membership_id.benefit_ids:
                used = 0
                if benefit.access_to == 'class':
                    domain = [
                        ('member_id', '=', member.id),
                        ('session_id.start_datetime', '>=', start_dt),
                        ('session_id.start_datetime', '<=', end_dt),
                        ('state', 'in', ['confirmed', 'attended']),
                    ]
                    if benefit.class_ids:
                        domain.append(('session_id.class_id', 'in', benefit.class_ids.ids))
                    used = Enrollment.search_count(domain)
                elif benefit.access_to == 'service':
                    domain = [
                        ('member_id', '=', member.id),
                        ('start_datetime', '>=', start_dt),
                        ('start_datetime', '<=', end_dt),
                        ('state', 'not in', ['draft', 'canceled']),
                    ]
                    if benefit.service_ids:
                        domain.append(('service_id', 'in', benefit.service_ids.ids))
                    used = self.env['gym.service.booking'].search_count(domain)
                elif benefit.access_to == 'door':
                    visitor_domain = [
                        ('member_id', '=', member.id),
                        ('checkin_time', '>=', start_dt),
                        ('checkin_time', '<=', end_dt),
                    ]
                    if not benefit.door_all and benefit.door_id:
                        visitor_domain.append(('door_id', '=', benefit.door_id.id))
                    used = self.env['gym.visitor'].search_count(visitor_domain)

                self.create({
                    'member_id': member.id,
                    'subscription_id': sub.id,
                    'benefit_id': benefit.id,
                    'used_count': used,
                })
