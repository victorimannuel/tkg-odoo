from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, time


class GymMembershipSubscription(models.Model):
    _name = 'gym.membership.subscription'
    _description = 'Member Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    member_id = fields.Many2one('gym.member', string='Member', required=True)
    membership_id = fields.Many2one('gym.membership', string='Membership', required=True)
    membership_category_id = fields.Many2one(
        'product.category', 
        related='membership_id.category_id', 
        string='Category', 
        store=True, 
        readonly=False
    )

    date_start = fields.Date(string='Start Date', default=fields.Date.context_today, required=True)
    date_end = fields.Date(string='End Date', compute='_compute_date_end', store=True, readonly=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('frozen', 'Frozen'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled')
    ], string='Status', default='draft', tracking=True)

    price = fields.Float(string='Price')

    total_sessions = fields.Integer(string='Total Sessions')
    remaining_sessions = fields.Integer(string='Remaining Sessions', compute='_compute_remaining_sessions', store=True)
    visits_used = fields.Integer(string='Visits Used', compute='_compute_visit_usage', store=False)
    visit_limit = fields.Integer(string='Visit Limit', compute='_compute_visit_usage', store=False)
    visit_usage_display = fields.Char(string='Visit Usage', compute='_compute_visit_usage', store=False)

    invoice_ids = fields.One2many('account.move', 'gym_subscription_id', string='Invoices')
    freeze_ids = fields.One2many('gym.membership.subscription.freeze', 'subscription_id', string='Freeze Requests')

    @api.depends('name', 'membership_id.name')
    def _compute_display_name(self):
        for sub in self:
            if sub.membership_id:
                sub.display_name = f"{sub.membership_id.name}"
            else:
                sub.display_name = sub.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gym.membership.subscription') or 'New'
        return super().create(vals_list)

    def action_cancel(self):
        for sub in self:
            if sub.state != 'canceled':
                draft_invoices = sub.invoice_ids.filtered(lambda m: m.state == 'draft')
                if draft_invoices:
                    draft_invoices.write({'state': 'cancel'})
                sub.state = 'canceled'

    def action_reset_to_draft(self):
        for sub in self:
            if sub.state == 'canceled':
                sub.state = 'draft'

    def action_delete(self):
        for sub in self:
            if sub.state != 'canceled':
                raise UserError(_("You can only delete subscriptions with status Canceled."))
        self.unlink()

    def unlink(self):
        not_canceled = self.filtered(lambda s: s.state != 'canceled')
        if not_canceled:
            raise UserError(_("You can only delete subscriptions with status Canceled."))
        for sub in self:
            canceled_invoices = sub.invoice_ids.filtered(lambda m: m.state == 'cancel')
            if canceled_invoices:
                canceled_invoices.unlink()
        return super().unlink()

    @api.onchange('membership_id')
    def _onchange_membership_id(self):
        if self.membership_id:
            self.price = self.membership_id.price
            self.total_sessions = self.membership_id.session_count

    @api.depends('date_start', 'membership_id')
    def _compute_date_end(self):
        for sub in self:
            if sub.membership_id.basis == 'renewal_based' and sub.date_start and sub.membership_id.duration:
                delta = {
                    'days': relativedelta(days=sub.membership_id.duration),
                    'weeks': relativedelta(weeks=sub.membership_id.duration),
                    'months': relativedelta(months=sub.membership_id.duration),
                    'years': relativedelta(years=sub.membership_id.duration),
                }
                sub.date_end = sub.date_start + delta.get(sub.membership_id.duration_uom)
            # elif sub.membership_id.basis == 'punch':
            #     sub.date_end = False

    @api.depends('total_sessions')
    def _compute_remaining_sessions(self):
        for sub in self:
            used = 0
            sub.remaining_sessions = sub.total_sessions - used

    @api.depends('member_id', 'membership_id', 'date_start', 'date_end')
    def _compute_visit_usage(self):
        today = fields.Date.context_today(self)
        for sub in self:
            start_date = sub.date_start
            end_date = sub.date_end or today
            if end_date < start_date:
                end_date = start_date
            
            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            # Count Class Enrollments
            enroll_count = self.env['gym.class.enrollment'].search_count([
                ('member_id', '=', sub.member_id.id),
                ('session_id.start_datetime', '>=', start_dt),
                ('session_id.start_datetime', '<=', end_dt),
                ('state', 'in', ['confirmed', 'attended']),
            ])
            
            # Count Service Bookings
            booking_count = self.env['gym.service.booking'].search_count([
                ('member_id', '=', sub.member_id.id),
                ('start_datetime', '>=', start_dt),
                ('start_datetime', '<=', end_dt),
                ('state', 'not in', ['draft', 'canceled']),
            ])
            
            sub.visits_used = enroll_count + booking_count
            
            limit = sub.membership_id.usage_limit or sub.membership_id.session_count or 0
            sub.visit_limit = limit
            if limit > 0:
                sub.visit_usage_display = f"{sub.visits_used} / {limit}"
            else:
                sub.visit_usage_display = f"{sub.visits_used} / ∞"

    def action_confirm(self):
        self.write({'state': 'running'})
        self._create_invoice()
        for sub in self:
            self.env['gym.membership.benefit.usage'].recompute_for_member(sub.member_id)

    def _create_invoice(self):
        for sub in self:
            if not sub.membership_id.product_id:
                continue

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': sub.member_id.partner_id.id,
                'gym_subscription_id': sub.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': sub.membership_id.product_id.id,
                        'name': f"Membership: {sub.membership_id.name}",
                        'quantity': 1,
                        'price_unit': sub.price,
                    })
                ],
            }
            self.env['account.move'].create(invoice_vals)

    @api.model
    def _cron_check_expiry(self):
        today = fields.Date.context_today(self)

        expired_subs = self.search([
            ('state', '=', 'running'),
            ('date_end', '<', today),
            ('date_end', '!=', False)
        ])
        expired_subs.write({'state': 'expired'})

        reminder_date = today + relativedelta(days=7)
        expiring_soon = self.search([
            ('state', '=', 'running'),
            ('date_end', '=', reminder_date)
        ])
        for sub in expiring_soon:
            sub.message_post(body="Membership expiring in 7 days!", partner_ids=[sub.member_id.partner_id.id])

    def action_freeze(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Freeze Subscription',
            'res_model': 'gym.membership.subscription.freeze',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id}
        }

    def action_view_usage(self):
        self.ensure_one()
        domain = [
            ('member_id', '=', self.member_id.id),
            ('state', 'in', ['confirmed', 'attended']),
        ]
        if self.date_start:
            start_dt = datetime.combine(self.date_start, time.min)
            domain.append(('session_id.start_datetime', '>=', start_dt))
        if self.date_end:
            end_dt = datetime.combine(self.date_end, time.max)
            domain.append(('session_id.start_datetime', '<=', end_dt))
        return {
            'name': _('Class Enrollments - %s') % self.membership_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'gym.class.enrollment',
            'view_mode': 'list',
            'domain': domain,
            'context': {'create': False},
        }
