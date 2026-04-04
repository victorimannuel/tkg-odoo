from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GymMembershipBenefit(models.Model):
    _name = 'gym.membership.benefit'
    _description = 'Membership Benefit'
    
    membership_id = fields.Many2one('gym.membership', string='Membership', required=True, ondelete='cascade')
    name = fields.Char(string='Benefit', compute='_compute_name', store=True, readonly=False)
    access_to = fields.Selection([
        ('door', 'Physical Door'),
        ('class', 'Classes'),
        ('service', 'Services'),
    ], string='Get Access To', required=True)
    class_category_id = fields.Many2one('product.category', string='Class Category', domain="[('gym_category_type', '=', 'class')]")
    service_category_id = fields.Many2one('product.category', string='Service Category', domain="[('gym_category_type', '=', 'service')]")
    door_all = fields.Boolean(string='All Doors', default=False)
    door_id = fields.Many2one('gym.door', string='Door', domain="[('active','=',True)]")
    class_ids = fields.Many2many('gym.class', string='Classes', domain="[('active','=',True)]")
    service_ids = fields.Many2many('gym.service', string='Services', domain="[('active', '=', True)]")

    @api.depends('access_to', 'door_all', 'door_id', 'class_ids', 'service_ids', 'class_category_id', 'service_category_id')
    def _compute_name(self):
        for rec in self:
            if rec.access_to == 'door':
                if rec.door_id:
                    rec.name = "Door: %s" % rec.door_id.name
                elif rec.door_all:
                    rec.name = "All Doors"
                else:
                    rec.name = "Door Access"
            elif rec.access_to == 'class' and rec.class_ids:
                if rec.class_category_id:
                    all_classes_in_categ = self.env['gym.class'].search([('category_id', '=', rec.class_category_id.id), ('active', '=', True)])
                    if set(rec.class_ids.ids) == set(all_classes_in_categ.ids):
                        rec.name = "All %s Classes" % rec.class_category_id.name
                        continue
                class_names = ", ".join(rec.class_ids.mapped('name'))
                rec.name = "Classes: %s" % class_names
            elif rec.access_to == 'class':
                rec.name = "Class Access"
            elif rec.access_to == 'service' and rec.service_ids:
                if rec.service_category_id:
                    all_services_in_categ = self.env['gym.service'].search([('category_id', '=', rec.service_category_id.id), ('active', '=', True)])
                    if set(rec.service_ids.ids) == set(all_services_in_categ.ids):
                        rec.name = "All %s Services" % rec.service_category_id.name
                        continue
                rec.name = "Services: %s" % ", ".join(rec.service_ids.mapped('name'))
            elif rec.access_to == 'service':
                rec.name = "Service Access"
            else:
                rec.name = "New Benefit"

    @api.constrains('access_to', 'membership_id', 'door_id', 'class_ids', 'service_ids')
    def _check_access_to(self):
        for rec in self:
            if rec.access_to == 'door':
                if not rec.door_all and not rec.door_id:
                    raise ValidationError(_("Door is required unless 'All Doors' is checked"))
                if rec.class_ids or rec.service_ids:
                    raise ValidationError(_("Only door is allowed for this benefit"))
            elif rec.access_to == 'class':
                if not rec.class_ids:
                    raise ValidationError(_("At least one class is required for class access"))
                if rec.door_id or rec.service_ids:
                    raise ValidationError(_("Only class is allowed for this benefit"))
            elif rec.access_to == 'service':
                if not rec.service_ids:
                    raise ValidationError(_("Service is required for service access"))
                if rec.door_id or rec.class_ids:
                    raise ValidationError(_("Only service is allowed for this benefit"))

    @api.onchange('access_to')
    def _onchange_access_to(self):
        for rec in self:
            if rec.access_to == 'door':
                rec.door_id = False # Added this line to clear door_id when access_to changes to door
                rec.door_all = False
                rec.class_category_id = False
                rec.class_ids = False
                rec.service_category_id = False
                rec.service_ids = False
            elif rec.access_to == 'class':
                rec.door_id = False
                rec.door_all = False
                rec.service_category_id = False
                rec.service_ids = False
            elif rec.access_to == 'service':
                rec.door_id = False
                rec.door_all = False
                rec.class_category_id = False
                rec.class_ids = False

    @api.onchange('class_category_id')
    def _onchange_class_category_id(self):
        if self.class_category_id:
            self.class_ids = False

    @api.onchange('service_category_id')
    def _onchange_service_category_id(self):
        if self.service_category_id:
            self.service_ids = False

    @api.onchange('door_all')
    def _onchange_door_all(self):
        for rec in self:
            if rec.door_all:
                rec.door_id = False
