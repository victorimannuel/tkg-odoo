from odoo import _, api, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.model
    def create_sale_order_from_pos_cart(self, config_id, payload):
        if not isinstance(payload, dict):
            raise UserError(_("Invalid payload format."))

        config = self.browse(int(config_id)).exists()
        if not config:
            raise UserError(_("POS configuration not found."))

        partner_id = int(payload.get("partner_id") or 0)
        partner = self.env["res.partner"].browse(partner_id).exists()
        if not partner:
            raise UserError(_("Please select a customer before creating a sale order."))

        raw_lines = payload.get("lines") or []
        if not isinstance(raw_lines, list) or not raw_lines:
            raise UserError(_("Your cart is empty. Add at least one product."))

        line_commands = []
        for raw_line in raw_lines:
            if not isinstance(raw_line, dict):
                continue

            product_id = int(raw_line.get("product_id") or 0)
            product = self.env["product.product"].browse(product_id).exists()
            if not product:
                continue
            if not product.sale_ok:
                raise UserError(
                    _("Product '%s' cannot be sold in Sales Orders.") % (product.display_name,)
                )

            qty = float(raw_line.get("qty") or 0.0)
            if qty <= 0:
                continue

            price_unit = float(raw_line.get("price_unit") or 0.0)
            discount = max(0.0, min(100.0, float(raw_line.get("discount") or 0.0)))
            description = (raw_line.get("description") or "").strip()

            line_vals = {
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom_id": product.uom_id.id,
                "price_unit": price_unit,
                "discount": discount,
            }
            if description:
                line_vals["name"] = description

            tax_ids = []
            for tax_id in raw_line.get("tax_ids") or []:
                try:
                    tax_ids.append(int(tax_id))
                except (TypeError, ValueError):
                    continue

            if tax_ids:
                taxes = self.env["account.tax"].browse(tax_ids).exists().filtered(
                    lambda t: t.company_id.id == config.company_id.id
                )
                line_vals["tax_ids"] = [(6, 0, taxes.ids)]

            line_commands.append((0, 0, line_vals))

        if not line_commands:
            raise UserError(_("No valid order lines found to create a Sale Order."))

        order_vals = {
            "partner_id": partner.id,
            "company_id": config.company_id.id,
            "origin": (payload.get("origin") or "").strip() or _("POS Cart"),
            "order_line": line_commands,
        }

        if config.crm_team_id:
            order_vals["team_id"] = config.crm_team_id.id

        pricelist_id = int(payload.get("pricelist_id") or 0)
        if pricelist_id:
            pricelist = self.env["product.pricelist"].browse(pricelist_id).exists()
            if pricelist:
                order_vals["pricelist_id"] = pricelist.id

        fiscal_position_id = int(payload.get("fiscal_position_id") or 0)
        if fiscal_position_id:
            fiscal_position = self.env["account.fiscal.position"].browse(fiscal_position_id).exists()
            if fiscal_position:
                order_vals["fiscal_position_id"] = fiscal_position.id

        note = (payload.get("note") or "").strip()
        if note:
            order_vals["note"] = note

        sale_order = self.env["sale.order"].create(order_vals)
        return {"sale_order_id": sale_order.id, "sale_order_name": sale_order.name}
