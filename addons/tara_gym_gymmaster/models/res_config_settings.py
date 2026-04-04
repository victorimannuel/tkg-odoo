from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    gymmaster_base_url = fields.Char(
        string="GymMaster Base URL",
        config_parameter="gymmaster.base_url",
    )
    gymmaster_api_key = fields.Char(
        string="GymMaster API Key",
        config_parameter="gymmaster.api_key",
    )

    def action_sync_gymmaster_members(self):
        self.ensure_one()
        if not self.gymmaster_base_url or not self.gymmaster_api_key:
            raise UserError("Please configure GymMaster Base URL and API Key first.")
        self.env["gymmaster.sync"].sync_members(batch_size=1000)

    def action_sync_gymmaster_memberships(self):
        self.ensure_one()
        if not self.gymmaster_base_url or not self.gymmaster_api_key:
            raise UserError("Please configure GymMaster Base URL and API Key first.")
        self.env["gymmaster.sync"].sync_memberships(batch_size=1000)

    def action_sync_gymmaster_member_photos(self):
        self.ensure_one()
        if not self.gymmaster_base_url or not self.gymmaster_api_key:
            raise UserError("Please configure GymMaster Base URL and API Key first.")
        self.env["gymmaster.sync"].sync_member_photos()

    def action_sync_gymmaster_products(self):
        self.ensure_one()
        if not self.gymmaster_base_url or not self.gymmaster_api_key:
            raise UserError("Please configure GymMaster Base URL and API Key first.")
        self.env["gymmaster.sync"].sync_products(batch_size=1000)

    def action_purge_gym_data(self):
        self.ensure_one()
        Subscription = self.env["gym.membership.subscription"]
        Membership = self.env["gym.membership"]
        Service = self.env["gym.service"]
        Class = self.env["gym.class"]
        Category = self.env["product.category"]
        Member = self.env["gym.member"]
        Invoice = self.env["account.move"]
        subscriptions = Subscription.search([])
        if subscriptions:
            invoices = Invoice.search([("gym_subscription_id", "in", subscriptions.ids)])
            for inv in invoices:
                if inv.state not in ("draft", "cancel"):
                    inv.button_cancel()
            invoices.unlink()
            subscriptions.action_cancel()
            subscriptions.unlink()
        
        # Unlink memberships
        memberships = Membership.search([])
        memberships.unlink()
        membership_products = memberships.mapped("product_id")
        if membership_products:
            membership_products.unlink()

        # Unlink members
        members = Member.search([])
        members.unlink()
        member_partners = members.mapped("partner_id")
        if member_partners:
            member_partners.unlink()
        
        # Unlink services
        services = Service.search([])
        services.unlink()

        # Unlink classes
        classes = Class.search([])
        classes.unlink()

        # Unlink additional gym transactional data
        self.env['gym.class.enrollment'].search([]).unlink()
        self.env['gym.class.session'].search([]).unlink()
        self.env['gym.visitor'].search([]).unlink()
        self.env['gym.membership.benefit.usage'].search([]).unlink()
        self.env['gym.service.booking'].search([]).unlink()
        self.env['gym.trainer.session'].search([]).unlink()
                
        # Unlink categories
        categories = Category.search([("gym_category_type", "in", ["membership", "class", "service"])])
        categories.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Gym data successfully purged!"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_purge_products(self):
        self.ensure_one()
        Product = self.env["product.product"].sudo()
        products = Product.search([("gymmaster_product_id", "!=", False)])
        if products:
            products.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("GymMaster products successfully purged!"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
