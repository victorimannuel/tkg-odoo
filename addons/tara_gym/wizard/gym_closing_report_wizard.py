import calendar
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models


class GymClosingReportWizard(models.TransientModel):
    _name = 'gym.closing.report.wizard'
    _description = 'Gym Closing Report Wizard'

    _FNB_CATEGORY_NAMES = {
        '1%',
        'CAKES',
        'COFFEES/TEAS',
        'DRINKS',
        'PROTEIN BAR',
        'SHAKER PROTEIN',
        'SNACKS',
        'SUPPLEMENTS',
    }
    _FNB_NAME_KEYWORDS = (
        'AQUA',
        'BALIAN',
        'CAKE',
        'CAPPUCCINO',
        'COFFEE',
        'CUP',
        'ESPRESSO',
        'LATTE',
        'MILK',
        'MOCHA',
        'NITROTECH',
        'OAT',
        'POCARI',
        'PROTEIN',
        'SHAKE',
        'SMOOTHIE',
        'TEA',
        'WATER',
    )

    report_date = fields.Date(
        string='Report Date',
        required=True,
        default=fields.Date.context_today,
    )
    staff_count = fields.Integer(string='Staff / Team', compute='_compute_report_data')
    checkin_count = fields.Integer(string='Check-ins', compute='_compute_report_data')
    open_gym_count = fields.Integer(string='Open Gym', compute='_compute_report_data')
    new_member_count = fields.Integer(string='New Members', compute='_compute_report_data')
    renew_member_count = fields.Integer(string='Renew Members', compute='_compute_report_data')

    slot_0600_0800 = fields.Integer(string='06.00 - 08.00', compute='_compute_report_data')
    slot_0800_1000 = fields.Integer(string='08.00 - 10.00', compute='_compute_report_data')
    slot_1000_1200 = fields.Integer(string='10.00 - 12.00', compute='_compute_report_data')
    slot_1200_1400 = fields.Integer(string='12.00 - 14.00', compute='_compute_report_data')
    slot_1400_1600 = fields.Integer(string='14.00 - 16.00', compute='_compute_report_data')
    slot_1600_1800 = fields.Integer(string='16.00 - 18.00', compute='_compute_report_data')
    slot_1800_2000 = fields.Integer(string='18.00 - 20.00', compute='_compute_report_data')

    memberships_total = fields.Float(string='Memberships / Passes', compute='_compute_report_data')
    memberships_lines = fields.Text(
        string='Memberships / Passes Breakdown',
        compute='_compute_report_data',
    )
    fnb_total = fields.Float(string='F&B', compute='_compute_report_data')
    fnb_lines = fields.Text(
        string='F&B Breakdown',
        compute='_compute_report_data',
    )
    products_total = fields.Float(string='Products', compute='_compute_report_data')
    products_lines = fields.Text(
        string='Products Breakdown',
        compute='_compute_report_data',
    )

    mtd_membership_total = fields.Float(string='Month to Date Membership', compute='_compute_report_data')
    mtd_fnb_total = fields.Float(string='Month to Date F&B', compute='_compute_report_data')
    mtd_product_total = fields.Float(string='Month to Date Product', compute='_compute_report_data')

    total_revenue = fields.Float(string='Total Revenue', compute='_compute_report_data')
    grand_total = fields.Float(string='Grand Total', compute='_compute_report_data')
    daily_average = fields.Float(string='Daily Average', compute='_compute_report_data')

    report_date_label = fields.Char(string='Report Date Label', compute='_compute_labels')
    mtd_period_label = fields.Char(string='MTD Period Label', compute='_compute_labels')

    def _get_user_timezone(self):
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        return pytz.timezone(tz_name)

    def _get_utc_range_for_local_date(self, report_date):
        timezone = self._get_user_timezone()
        local_start = timezone.localize(datetime.combine(report_date, time.min))
        local_end = local_start + timedelta(days=1)
        return (
            local_start.astimezone(pytz.UTC).replace(tzinfo=None),
            local_end.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    def _format_quantity(self, quantity):
        rounded = round(quantity)
        if abs(quantity - rounded) < 1e-9:
            return str(int(rounded))
        return f"{quantity:.2f}".rstrip('0').rstrip('.')

    def _dict_to_lines(self, quantities):
        lines = []
        for name in sorted(quantities):
            qty = quantities[name]
            if abs(qty) < 1e-9:
                continue
            lines.append(f"{name} = {self._format_quantity(qty)}")
        return "\n".join(lines)

    def _classify_non_gym_product(self, product):
        category_name = (product.categ_id.name or '').strip().upper()
        product_name = (product.display_name or product.name or '').strip().upper()
        if category_name in self._FNB_CATEGORY_NAMES:
            return 'fnb'
        if any(keyword in product_name for keyword in self._FNB_NAME_KEYWORDS):
            return 'fnb'
        return 'product'

    def _collect_membership_data(self, start_dt, end_dt):
        subscriptions = self.env['gym.membership.subscription'].sudo().search([
            ('create_date', '>=', start_dt),
            ('create_date', '<', end_dt),
            ('state', '!=', 'canceled'),
        ])
        quantities = defaultdict(float)
        new_members = 0
        renew_members = 0
        total = 0.0

        for sub in subscriptions:
            quantities[sub.membership_id.display_name or sub.membership_id.name or 'Membership'] += 1
            total += sub.price
            member_created = fields.Datetime.context_timestamp(sub, sub.member_id.create_date)
            if member_created.date() == self.report_date:
                new_members += 1
            else:
                renew_members += 1

        return {
            'subscriptions': subscriptions,
            'lines': self._dict_to_lines(quantities),
            'new_member_count': new_members,
            'renew_member_count': renew_members,
            'total': total,
        }

    def _collect_pos_data(self, start_dt, end_dt):
        line_model = self.env['pos.order.line'].sudo()
        lines = line_model.search([
            ('order_id.date_order', '>=', start_dt),
            ('order_id.date_order', '<', end_dt),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
        ])

        gym_product_ids = set(self.env['gym.membership'].sudo().search([]).mapped('product_id').ids)
        gym_product_ids.update(self.env['gym.class'].sudo().search([]).mapped('product_id').ids)
        gym_product_ids.update(self.env['gym.service'].sudo().search([]).mapped('product_id').ids)

        fnb_quantities = defaultdict(float)
        product_quantities = defaultdict(float)
        fnb_total = 0.0
        product_total = 0.0

        for line in lines:
            product = line.product_id
            if not product or product.id in gym_product_ids:
                continue

            section = self._classify_non_gym_product(product)
            line_total = line.price_subtotal_incl
            qty = line.qty
            name = product.display_name or product.name or 'Unnamed Product'

            if section == 'fnb':
                fnb_quantities[name] += qty
                fnb_total += line_total
            else:
                product_quantities[name] += qty
                product_total += line_total

        return {
            'orders': lines.mapped('order_id'),
            'fnb_lines': self._dict_to_lines(fnb_quantities),
            'fnb_total': fnb_total,
            'products_lines': self._dict_to_lines(product_quantities),
            'products_total': product_total,
        }

    def _collect_visit_data(self, start_dt, end_dt):
        visitors = self.env['gym.visitor'].sudo().search([
            ('checkin_time', '>=', start_dt),
            ('checkin_time', '<', end_dt),
        ])
        slot_counts = {
            'slot_0600_0800': 0,
            'slot_0800_1000': 0,
            'slot_1000_1200': 0,
            'slot_1200_1400': 0,
            'slot_1400_1600': 0,
            'slot_1600_1800': 0,
            'slot_1800_2000': 0,
        }

        for visitor in visitors:
            local_dt = fields.Datetime.context_timestamp(visitor, visitor.checkin_time)
            hour = local_dt.hour
            if 6 <= hour < 8:
                slot_counts['slot_0600_0800'] += 1
            elif 8 <= hour < 10:
                slot_counts['slot_0800_1000'] += 1
            elif 10 <= hour < 12:
                slot_counts['slot_1000_1200'] += 1
            elif 12 <= hour < 14:
                slot_counts['slot_1200_1400'] += 1
            elif 14 <= hour < 16:
                slot_counts['slot_1400_1600'] += 1
            elif 16 <= hour < 18:
                slot_counts['slot_1600_1800'] += 1
            elif 18 <= hour < 20:
                slot_counts['slot_1800_2000'] += 1

        slot_counts.update({
            'visitors': visitors,
            'checkin_count': len(visitors),
            'open_gym_count': len(visitors.filtered(lambda v: not v.session_id)),
        })
        return slot_counts

    @api.depends('report_date')
    def _compute_report_data(self):
        for wizard in self:
            if not wizard.report_date:
                wizard.staff_count = 0
                wizard.checkin_count = 0
                wizard.open_gym_count = 0
                wizard.new_member_count = 0
                wizard.renew_member_count = 0
                wizard.slot_0600_0800 = 0
                wizard.slot_0800_1000 = 0
                wizard.slot_1000_1200 = 0
                wizard.slot_1200_1400 = 0
                wizard.slot_1400_1600 = 0
                wizard.slot_1600_1800 = 0
                wizard.slot_1800_2000 = 0
                wizard.memberships_total = 0.0
                wizard.memberships_lines = False
                wizard.fnb_total = 0.0
                wizard.fnb_lines = False
                wizard.products_total = 0.0
                wizard.products_lines = False
                wizard.mtd_membership_total = 0.0
                wizard.mtd_fnb_total = 0.0
                wizard.mtd_product_total = 0.0
                wizard.total_revenue = 0.0
                wizard.grand_total = 0.0
                wizard.daily_average = 0.0
                continue

            report_date = fields.Date.to_date(wizard.report_date)
            day_start, day_end = wizard._get_utc_range_for_local_date(report_date)
            month_start = report_date.replace(day=1)
            month_start_dt, _ = wizard._get_utc_range_for_local_date(month_start)

            daily_membership = wizard._collect_membership_data(day_start, day_end)
            daily_pos = wizard._collect_pos_data(day_start, day_end)
            daily_visit = wizard._collect_visit_data(day_start, day_end)

            mtd_membership = wizard._collect_membership_data(month_start_dt, day_end)
            mtd_pos = wizard._collect_pos_data(month_start_dt, day_end)

            staff_user_ids = set(daily_membership['subscriptions'].mapped('create_uid').ids)
            staff_user_ids.update(daily_pos['orders'].mapped('create_uid').ids)
            staff_user_ids.update(daily_visit['visitors'].mapped('create_uid').ids)

            wizard.staff_count = len(staff_user_ids)
            wizard.checkin_count = daily_visit['checkin_count']
            wizard.open_gym_count = daily_visit['open_gym_count']
            wizard.new_member_count = daily_membership['new_member_count']
            wizard.renew_member_count = daily_membership['renew_member_count']
            wizard.slot_0600_0800 = daily_visit['slot_0600_0800']
            wizard.slot_0800_1000 = daily_visit['slot_0800_1000']
            wizard.slot_1000_1200 = daily_visit['slot_1000_1200']
            wizard.slot_1200_1400 = daily_visit['slot_1200_1400']
            wizard.slot_1400_1600 = daily_visit['slot_1400_1600']
            wizard.slot_1600_1800 = daily_visit['slot_1600_1800']
            wizard.slot_1800_2000 = daily_visit['slot_1800_2000']

            wizard.memberships_total = daily_membership['total']
            wizard.memberships_lines = daily_membership['lines']
            wizard.fnb_total = daily_pos['fnb_total']
            wizard.fnb_lines = daily_pos['fnb_lines']
            wizard.products_total = daily_pos['products_total']
            wizard.products_lines = daily_pos['products_lines']

            wizard.mtd_membership_total = mtd_membership['total']
            wizard.mtd_fnb_total = mtd_pos['fnb_total']
            wizard.mtd_product_total = mtd_pos['products_total']

            wizard.total_revenue = (
                wizard.memberships_total
                + wizard.fnb_total
                + wizard.products_total
            )
            wizard.grand_total = (
                wizard.mtd_membership_total
                + wizard.mtd_fnb_total
                + wizard.mtd_product_total
            )
            wizard.daily_average = wizard.grand_total / report_date.day if report_date.day else 0.0

    @api.depends('report_date')
    def _compute_labels(self):
        for wizard in self:
            if wizard.report_date:
                report_date = fields.Date.to_date(wizard.report_date)
                wizard.report_date_label = (
                    f"{calendar.day_name[report_date.weekday()]}, "
                    f"{report_date.day:02d} "
                    f"{calendar.month_name[report_date.month]} "
                    f"{report_date.year}"
                )
                wizard.mtd_period_label = (
                    f"1 - {report_date.day} "
                    f"{calendar.month_name[report_date.month]} "
                    f"{report_date.year}"
                )
            else:
                wizard.report_date_label = False
                wizard.mtd_period_label = False

    def format_idr(self, amount):
        self.ensure_one()
        return f"IDR {amount:,.0f}"

    def detail_lines(self, text):
        self.ensure_one()
        return [line.strip() for line in (text or '').splitlines() if line.strip()]

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('tara_gym.action_report_gym_closing_report').report_action(self)
