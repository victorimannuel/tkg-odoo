from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request

class GymMember(models.Model):
    _name = 'gym.member'
    _description = 'Gym Member'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    
    # Member specific fields
    active = fields.Boolean(default=True)
    firstname = fields.Char(string='First Name', required=True)
    surname = fields.Char(string='Last Name')
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True)
    member_code = fields.Char(string='Member ID', readonly=True, copy=False, default='New')
    date_of_birth = fields.Date(string='Date of Birth')
    join_date = fields.Date(string='Join Date', default=fields.Date.context_today)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', required=True)

    marketing_source = fields.Selection([
        ('friend', 'A Friend'),
        ('google_adwords', 'Google Adwords'),
        ('social_media', 'Social Media'),
        ('leaflet', 'Leaflet'),
        ('mail_promotion', 'Mail Promotion'),
        ('online_signup', 'Online Signup'),
        ('walk_in_drive_by', 'Walk In / Drive By'),
        ('website', 'Website'),
    ], string='Source Promotion')
    referrer_member_id = fields.Many2one('gym.member', string='Referred By Member')
    
    # # Address and Contact Info (Handled via res.partner, but shown for clarity)
    # email = fields.Char(related='partner_id.email', readonly=False)
    # mobile = fields.Char(related='partner_id.mobile', readonly=False)
    # phone = fields.Char(related='partner_id.phone', readonly=False)
    # street = fields.Char(related='partner_id.street', readonly=False)
    # street2 = fields.Char(related='partner_id.street2', readonly=False, string='Suburb')
    # city = fields.Char(related='partner_id.city', readonly=False)
    # zip = fields.Char(related='partner_id.zip', readonly=False)
    
    # # Additional Info
    # notes = fields.Text(string='Notes')
    # medical_info = fields.Text(string='Medical Information')

    @api.onchange('firstname', 'surname')
    def _onchange_complete_name(self):
        names = [n for n in [self.firstname, self.surname] if n]
        self.name = " ".join(names)

    @api.depends('firstname', 'surname')
    def _compute_complete_name(self):
        for member in self:
            names = [n for n in [member.firstname, member.surname] if n]
            full_name = " ".join(names)
            member.name = full_name
            member.complete_name = full_name

    def action_view_pos_orders(self):
        self.ensure_one()
        return self.partner_id.action_view_pos_order()
    
    tag_ids = fields.Many2many('gym.member.tag', string='Tags')
    health_ids = fields.One2many('gym.member.health', 'member_id', string='Health Profile')
    document_ids = fields.One2many('gym.member.document', 'member_id', string='Documents')
    subscription_ids = fields.One2many('gym.membership.subscription', 'member_id', string='Subscriptions')
    current_subscription_id = fields.Many2one(
        'gym.membership.subscription',
        string='Current Subscription',
        compute='_compute_current_membership',
        store=False,
    )
    current_subscription_membership_id = fields.Many2one(
        'gym.membership',
        string='Current Membership',
        compute='_compute_current_membership',
        store=False,
    )
    current_membership_benefit_ids = fields.One2many(
        'gym.membership.benefit.usage',
        'member_id',
        string='Current Membership Benefits',
    )
    visitor_ids = fields.One2many('gym.visitor', 'member_id', string='Visit History')
    visit_count = fields.Integer(compute='_compute_visit_count', string='Visit Count')
    is_checked_in = fields.Boolean(string='Is Inside', default=False)
 
    @api.depends('visitor_ids')
    def _compute_visit_count(self):
        for member in self:
            member.visit_count = len(member.visitor_ids)
    
    def action_view_visit(self):
        self.ensure_one()
        return {
            'name': _('Visit History'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.visitor',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_add_membership(self):
        self.ensure_one()
        quick_form = self.env.ref("tara_gym.view_gym_quick_add_membership_wizard_form")
        return {
            'name': _('Quick Add Membership'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.quick.add.membership.wizard',
            'view_mode': 'form',
            'view_id': quick_form.id,
            'target': 'new',
            'context': {
                'default_member_id': self.id,
                'default_is_new_member': False,
            },
        }

    def action_open_pos_with_customer(self):
        self.ensure_one()
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

        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id)],
            limit=1
        )

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

        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/ui/%d' % pos_config.id,
            'target': 'self',
        }

    def action_checkin(self):
        self.ensure_one()
        if self.is_checked_in:
            return True
        
        return {
            'name': _('Check-in Member'),
            'type': 'ir.actions.act_window',
            'res_model': 'gym.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_member_id': self.id,
                'default_method': 'manual',
            },
        }

    def action_refresh_benefits(self):
        for member in self:
            self.env['gym.membership.benefit.usage'].recompute_for_member(member)
        return True

    def action_quick_create_confirm(self):
        self.ensure_one()
        # The record is already created by Odoo if opened in target='new' form
        # but here we want to also enroll it to the session if context has session_id
        session_id = self.env.context.get('default_session_id')
        if session_id:
            self.env['gym.class.enrollment'].create({
                'session_id': session_id,
                'member_id': self.id,
                'state': 'draft'
            })
        return {'type': 'ir.actions.act_window_close'}

    def action_checkout(self):
        self.ensure_one()
        if not self.is_checked_in:
            return True
        active_visits = self.visitor_ids.filtered(lambda v: v.status == 'active')
        if active_visits:
            active_visits.write({'checkout_time': fields.Datetime.now()})
        self.is_checked_in = False
        return True

    membership_status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('frozen', 'Frozen'),
        ('canceled', 'Canceled'),
        ('none', 'No Membership')
    ], string='Membership Status', compute='_compute_membership_status', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        Tag = self.env['gym.member.tag']
        gym_tag = Tag.search([('name', '=', 'GYM')], limit=1)
        if not gym_tag:
            gym_tag = Tag.create({'name': 'GYM'})
        for vals in vals_list:
            if vals.get('member_code', 'New') == 'New':
                vals['member_code'] = self.env['ir.sequence'].next_by_code('gym.member') or 'New'
            
            # Ensure name is populated for res.partner
            if not vals.get('name'):
                firstname = vals.get('firstname') or ''
                surname = vals.get('surname') or ''
                name = f"{firstname} {surname}".strip()
                vals['name'] = name or 'New Member'
            if not vals.get('tag_ids'):
                vals['tag_ids'] = [(6, 0, [gym_tag.id])]

        return super().create(vals_list)

    @api.depends('subscription_ids.state', 'subscription_ids.date_end')
    def _compute_membership_status(self):
        for member in self:
            active_subs = member.subscription_ids.filtered(lambda s: s.state == 'running')
            if active_subs:
                member.membership_status = 'active'
            elif member.subscription_ids.filtered(lambda s: s.state == 'frozen'):
                member.membership_status = 'frozen'
            elif member.subscription_ids:
                member.membership_status = 'expired'
            else:
                member.membership_status = 'none'

    @api.depends('subscription_ids.state', 'subscription_ids.date_start')
    def _compute_current_membership(self):
        for member in self:
            running = member.subscription_ids.filtered(lambda s: s.state == 'running')
            if running:
                running = running.sorted(key=lambda s: s.date_start or s.create_date)
                current_sub = running[-1]
            else:
                current_sub = self.env['gym.membership.subscription']
            member.current_subscription_id = current_sub
            member.current_subscription_membership_id = current_sub.membership_id if current_sub else False
