from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GymClassEnrollmentCreateWizard(models.TransientModel):
    _name = 'gym.class.enrollment.create.wizard'
    _description = 'Class Enrollment Wizard'

    session_id = fields.Many2one('gym.class.session', string='Session', required=True)
    class_id = fields.Many2one('gym.class', related='session_id.class_id', readonly=True)

    # ── Member selection ──────────────────────────────────────────
    is_new_member = fields.Boolean(string='New Member', default=False)
    member_id = fields.Many2one('gym.member', string='Member')

    # Inline new member fields
    firstname = fields.Char(string='First Name')
    surname = fields.Char(string='Last Name')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    comment = fields.Text(string='Note')

    # ── Price / membership ────────────────────────────────────────
    price = fields.Float(string='Price', required=True)
    has_class_benefit = fields.Boolean(string='Covered by Membership', compute='_compute_has_class_benefit')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        session_id = self.env.context.get('default_session_id')
        if session_id:
            session = self.env['gym.class.session'].browse(session_id)
            res['price'] = session.class_id.price
        return res

    @api.depends('member_id', 'session_id', 'is_new_member')
    def _compute_has_class_benefit(self):
        for rec in self:
            if rec.is_new_member or not rec.member_id:
                rec.has_class_benefit = False
            else:
                rec.has_class_benefit = rec._check_class_benefit()

    def _check_class_benefit(self):
        """Check if member's active membership covers the session's class."""
        if not self.member_id or not self.session_id:
            return False
        membership = self.member_id.current_subscription_membership_id
        if not membership:
            return False
        class_benefits = membership.benefit_ids.filtered(lambda b: b.access_to == 'class')
        return any(self.session_id.class_id in b.class_ids for b in class_benefits)

    @api.onchange('member_id', 'session_id', 'is_new_member')
    def _onchange_member_session(self):
        if self.is_new_member:
            self.member_id = False
            self.price = self.session_id.class_id.price if self.session_id else 0
        elif self.member_id and self.session_id:
            if self._check_class_benefit():
                self.price = 0.0
            else:
                self.price = self.session_id.class_id.price

    def action_confirm(self):
        self.ensure_one()

        # Resolve or create member
        member = self._get_or_create_member()
        
        drop_in_membership_id = int(self.env['ir.config_parameter'].sudo().get_param('tara_gym.default_drop_in_membership_id', '0'))

        # Create enrollment as confirmed if free, or draft if paid via POS
        self.env['gym.class.enrollment'].create({
            'session_id': self.session_id.id,
            'member_id': member.id,
            'membership_id': drop_in_membership_id,
            'price': self.price,
            'state': 'draft' if self.price > 0 else 'confirmed',
        })

        # If there's a price to pay, redirect to POS
        if self.price > 0:
            return self._create_pos_order_and_redirect(member)

        return {'type': 'ir.actions.act_window_close'}

    def _get_or_create_member(self):
        """Return existing member or create a new one."""
        if not self.is_new_member:
            if not self.member_id:
                raise UserError(_("Please select a member."))
            return self.member_id

        if not self.firstname:
            raise UserError(_("First name is required for new members."))
        if not self.phone:
            raise UserError(_("Phone is required for new members."))

        vals = {
            'firstname': self.firstname,
            'surname': self.surname or '',
            'phone': self.phone,
            'email': self.email or '',
            'gender': self.gender or 'other',
        }
        if self.date_of_birth:
            vals['date_of_birth'] = self.date_of_birth
        if self.image_1920:
            vals['image_1920'] = self.image_1920
        if self.comment:
            vals['comment'] = self.comment
        member = self.env['gym.member'].create(vals)
        
        # Assign drop-in membership to the new member so they have an active subscription
        drop_in_id = int(self.env['ir.config_parameter'].sudo().get_param('tara_gym.default_drop_in_membership_id', '0'))
        if drop_in_id:
            membership = self.env['gym.membership'].browse(drop_in_id).exists()
            if membership:
                self.env['gym.membership.subscription'].create({
                    'member_id': member.id,
                    'membership_id': membership.id,
                    'state': 'draft' if self.price > 0 else 'running',
                    'date_start': fields.Date.context_today(self),
                    'date_end': fields.Date.context_today(self),
                })
        
        return member

    def _create_pos_order_and_redirect(self, member):
        """Create a POS order for the enrollment and redirect to POS UI."""
        pos_config_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'tara_gym.gym_pos_config_id', '0'
            )
        )
        if not pos_config_id:
            raise UserError(_("No POS Config set. Please configure it in Gym → Configuration → Settings."))

        pos_config = self.env['pos.config'].browse(pos_config_id).exists()
        if not pos_config:
            raise UserError(_("The configured POS Config no longer exists."))

        pos_session = pos_config.current_session_id
        if not pos_session or pos_session.state != 'opened':
            raise UserError(_("No open POS session found for '%s'. Please open a POS session first.", pos_config.name))

        product = self.class_id.product_id
        if not product:
            raise UserError(_("The class '%s' has no linked product.", self.class_id.name))

        pos_order = self.env['pos.order'].create({
            'session_id': pos_session.id,
            'partner_id': member.partner_id.id,
            'amount_tax': 0,
            'amount_total': self.price,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [(0, 0, {
                'product_id': product.id,
                'full_product_name': product.name,
                'qty': 1,
                'price_unit': self.price,
                'price_subtotal': self.price,
                'price_subtotal_incl': self.price,
            })],
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/ui/%d/product/%s' % (pos_config.id, pos_order.uuid),
            'target': 'new',
        }
