from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request


class GymQuickAddMembershipWizard(models.TransientModel):
    _name = 'gym.quick.add.membership.wizard'
    _description = 'Quick Add Membership Wizard'

    is_new_member = fields.Boolean(string='New Member', default=False)
    member_id = fields.Many2one('gym.member', string='Member')

    firstname = fields.Char(string='First Name')
    surname = fields.Char(string='Last Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    comment = fields.Text(string='Note')

    membership_category_id = fields.Many2one(
        'product.category',
        string='Membership Category',
        domain=[('gym_category_type', '=', 'membership')],
    )
    membership_id = fields.Many2one('gym.membership', string='Membership', required=True)
    price = fields.Float(string='Price')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        member_id = self.env.context.get('default_member_id')
        member = self.env['gym.member'].browse(member_id).exists() if member_id else False
        if member:
            if 'member_id' in fields_list:
                res['member_id'] = member.id
        
        if self.env.context.get('from_drop_in_menu'):
            drop_in_visit_membership_id = int(
                self.env['ir.config_parameter'].sudo().get_param(
                    'tara_gym.default_drop_in_visit_membership_id', '0'
                )
            )
            if drop_in_visit_membership_id and 'membership_id' in fields_list:
                res['membership_id'] = drop_in_visit_membership_id
                membership = self.env['gym.membership'].browse(drop_in_visit_membership_id).exists()
                if membership and 'membership_category_id' in fields_list:
                    res['membership_category_id'] = membership.category_id.id
            if 'is_new_member' in fields_list:
                res['is_new_member'] = True
        return res

    @api.onchange('membership_id')
    def _onchange_membership_id(self):
        if self.membership_id:
            self.membership_category_id = self.membership_id.category_id
            self.price = self.membership_id.price

    @api.onchange('membership_category_id')
    def _onchange_membership_category_id(self):
        if self.membership_id and self.membership_id.category_id != self.membership_category_id:
            self.membership_id = False
            self.price = 0.0

    @api.onchange('is_new_member')
    def _onchange_is_new_member(self):
        if self.is_new_member:
            self.member_id = False

    def _get_or_create_member(self):
        if not self.is_new_member:
            if not self.member_id:
                raise UserError(_("Please select a member."))
            return self.member_id

        if not self.firstname:
            raise UserError(_("First name is required for new members."))
        if not self.phone:
            raise UserError(_("Phone is required for new members."))
        if not self.gender:
            raise UserError(_("Gender is required for new members."))

        member_vals = {
            'firstname': self.firstname,
            'surname': self.surname or '',
            'email': self.email or '',
            'phone': self.phone,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'comment': self.comment or '',
        }
        if self.image_1920:
            member_vals['image_1920'] = self.image_1920
        return self.env['gym.member'].create(member_vals)

    def _create_pos_order_and_redirect(self, member, membership, amount_total):
        pos_config_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'tara_gym.gym_pos_config_id', '0'
            )
        )
        if not pos_config_id:
            raise UserError(_(
                "No POS Config set. "
                "Please configure it in Gym -> Configuration -> Settings."
            ))

        pos_config = self.env['pos.config'].browse(pos_config_id).exists()
        if not pos_config:
            raise UserError(_(
                "The configured POS Config no longer exists. "
                "Please update it in Gym -> Configuration -> Settings."
            ))

        pos_session = pos_config.current_session_id
        if not pos_session or pos_session.state != 'opened':
            raise UserError(_(
                "No open POS session found for '%s'. "
                "Please open a POS session first.",
                pos_config.name,
            ))

        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id)],
            limit=1
        )

        pos_order = self.env['pos.order'].create({
            'session_id': pos_session.id,
            'partner_id': member.partner_id.id,
            'amount_tax': 0,
            'amount_total': amount_total,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [(0, 0, {
                'product_id': membership.product_id.id,
                'full_product_name': membership.product_id.name,
                'qty': 1,
                'price_unit': amount_total,
                'price_subtotal': amount_total,
                'price_subtotal_incl': amount_total,
            })],
        })

        if request:
            request.session['tara_gym_auto_cashier'] = {
                'enabled': True,
                'employee_id': employee.id if employee else False,
            }
            if employee:
                # Compatibility hints for POS login route that may run before POS JS app boot.
                request.session['pos_employee_id'] = employee.id
                request.session['pos_hr_employee_id'] = employee.id
                request.session['cashier_employee_id'] = employee.id
                request.session['pos_user_id'] = self.env.user.id

        url = '/pos/ui/%d/product/%s#auto_cashier=1' % (pos_config.id, pos_order.uuid)
        if employee:
            url = '%s&cashier_employee_id=%s' % (url, employee.id)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def action_confirm(self):
        self.ensure_one()

        membership = self.membership_id.exists()
        if not membership:
            raise UserError(_("Please select a valid membership."))
        if not membership.product_id:
            raise UserError(_(
                "The membership '%s' has no linked product. "
                "Please configure a product for this membership.",
                membership.name,
            ))

        member = self._get_or_create_member()
        amount_total = self.price if self.price is not False else membership.price
        amount_total = max(amount_total, 0.0)

        sub = self.env['gym.membership.subscription'].create({
            'member_id': member.id,
            'membership_id': membership.id,
            'date_start': fields.Date.context_today(self),
            'price': amount_total,
            'total_sessions': membership.session_count,
        })

        if amount_total <= 0:
            sub.action_confirm()
            return {'type': 'ir.actions.act_window_close'}

        return self._create_pos_order_and_redirect(member, membership, amount_total)
