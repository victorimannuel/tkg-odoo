/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(PosStore.prototype, {
    _buildSaleOrderPayloadFromCurrentOrder(order) {
        const partner = order.getPartner();
        const lines = order
            .getOrderlines()
            .map((line) => ({
                product_id: line.getProduct()?.id || false,
                qty: Number(line.getQuantity() || 0),
                price_unit: Number(line.price_unit || 0),
                discount: Number(line.getDiscount() || 0),
                tax_ids: (line.tax_ids || []).map((tax) => tax.id).filter(Boolean),
                description: line.getFullProductName(),
            }))
            .filter((line) => line.product_id && line.qty > 0);

        return {
            partner_id: partner?.id || false,
            pricelist_id: order.pricelist_id?.id || false,
            fiscal_position_id: order.fiscal_position_id?.id || false,
            note: order.general_customer_note || "",
            origin: _t("POS Cart %s", order.name || "/"),
            lines,
        };
    },

    async createSaleOrderFromCurrentCart() {
        if (this._isCreatingSaleOrderFromCart) {
            return false;
        }

        const sourceOrder = this.getOrder();
        if (!sourceOrder || sourceOrder.isEmpty()) {
            throw new Error(_t("Your cart is empty. Add products first."));
        }

        if (!sourceOrder.getPartner()) {
            throw new Error(_t("Select a customer before creating a Sale Order."));
        }

        const payload = this._buildSaleOrderPayloadFromCurrentOrder(sourceOrder);
        if (!payload.lines.length) {
            throw new Error(_t("No valid saleable lines found in the cart."));
        }

        this._isCreatingSaleOrderFromCart = true;
        try {
            const result = await this.data.call(
                "pos.config",
                "create_sale_order_from_pos_cart",
                [this.config.id, payload],
                {},
                false
            );
            if (!result || !result.sale_order_id) {
                throw new Error(_t("Failed to create Sale Order."));
            }

            const createdName = result.sale_order_name || `#${result.sale_order_id}`;
            const newOrder = this.addNewOrder();
            if (sourceOrder && sourceOrder !== newOrder) {
                this.removeOrder(sourceOrder, false);
            }

            this.notification.add(_t("Sale Order %s created.", createdName), { type: "success" });
            return result;
        } finally {
            this._isCreatingSaleOrderFromCart = false;
        }
    },
});

patch(ControlButtons.prototype, {
    canCreateSaleOrderFromCart() {
        const order = this.currentOrder;
        return Boolean(
            order &&
                !order.isEmpty() &&
                order.getPartner() &&
                !this.pos._isCreatingSaleOrderFromCart &&
                this.pos.cashier?._role !== "minimal"
        );
    },

    async onClickCreateSaleOrderFromCart() {
        try {
            const confirmed = await ask(this.dialog, {
                title: _t("Create Sale Order"),
                body: _t(
                    "Create a draft Sale Order from this cart and clear the current POS order?"
                ),
                confirmLabel: _t("Create"),
                cancelLabel: _t("Cancel"),
            });
            if (!confirmed) {
                return;
            }
            await this.pos.createSaleOrderFromCurrentCart();
        } catch (error) {
            this.notification.add(error?.message || _t("Could not create Sale Order."), {
                type: "danger",
            });
        }
    },
});
