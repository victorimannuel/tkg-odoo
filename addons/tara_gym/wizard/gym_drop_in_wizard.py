from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GymDropInWizard(models.TransientModel):
    _name = 'gym.drop.in.wizard'
    _description = 'Drop-In Registration Wizard'

    firstname = fields.Char(string='First Name', required=True)
    surname = fields.Char(string='Last Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone', required=True)
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', required=True)
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    comment = fields.Text(string='Note')

    def action_confirm(self):
        self.ensure_one()

        # ── Validate POS config ──────────────────────────────────────
        pos_config_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'tara_gym.gym_pos_config_id', '0'
            )
        )
        if not pos_config_id:
            raise UserError(_(
                "No POS Config set. "
                "Please configure it in Gym → Configuration → Settings."
            ))

        pos_config = self.env['pos.config'].browse(pos_config_id).exists()
        if not pos_config:
            raise UserError(_(
                "The configured POS Config no longer exists. "
                "Please update it in Gym → Configuration → Settings."
            ))

        pos_session = pos_config.current_session_id
        if not pos_session or pos_session.state != 'opened':
            raise UserError(_(
                "No open POS session found for '%s'. "
                "Please open a POS session first.",
                pos_config.name,
            ))

        # ── Validate drop-in membership ──────────────────────────────
        membership_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'tara_gym.default_drop_in_visit_membership_id', '0'
            )
        )
        if not membership_id:
            raise UserError(_(
                "No Drop-In Membership configured. "
                "Please set it in Gym → Configuration → Settings."
            ))

        membership = self.env['gym.membership'].browse(membership_id).exists()
        if not membership:
            raise UserError(_(
                "The configured Drop-In Membership no longer exists. "
                "Please update it in Gym → Configuration → Settings."
            ))

        if not membership.product_id:
            raise UserError(_(
                "The Drop-In Membership '%s' has no linked product. "
                "Please configure a product for this membership.",
                membership.name,
            ))

        # ── Create member ────────────────────────────────────────────
        member_vals = {
            'firstname': self.firstname,
            'surname': self.surname or '',
            'email': self.email or '',
            'phone': self.phone or '',
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'comment': self.comment or '',
        }
        if self.image_1920:
            member_vals['image_1920'] = self.image_1920
        member = self.env['gym.member'].create(member_vals)

        # ── Create subscription (draft — confirmed after POS payment)
        self.env['gym.membership.subscription'].create({
            'member_id': member.id,
            'membership_id': membership.id,
            'date_start': fields.Date.context_today(self),
            'price': membership.price,
            'total_sessions': membership.session_count,
        })

        # ── Create POS order ─────────────────────────────────────────
        pos_order = self.env['pos.order'].create({
            'session_id': pos_session.id,
            'partner_id': member.partner_id.id,
            'amount_tax': 0,
            'amount_total': membership.price,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [(0, 0, {
                'product_id': membership.product_id.id,
                'full_product_name': membership.product_id.name,
                'qty': 1,
                'price_unit': membership.price,
                'price_subtotal': membership.price,
                'price_subtotal_incl': membership.price,
            })],
        })

        # ── Redirect to POS UI ───────────────────────────────────────
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/ui/%d/product/%s' % (pos_config.id, pos_order.uuid),
            'target': 'self',
        }
