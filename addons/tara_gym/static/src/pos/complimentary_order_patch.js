/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

export class ComplimentaryLineButton extends Component {
    static template = "tara_gym.ComplimentaryLineButton";
    static props = {
        active: { type: Boolean },
        disabled: { type: Boolean, optional: true },
        label: { type: String },
        onClick: { type: Function },
        class: { type: String, optional: true },
    };
}

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.is_complimentary = Boolean(this.is_complimentary);
        this.complimentary_value = Number(this.complimentary_value || 0);
        this._complimentary_prev_discount = null;
    },

    toggleComplimentary() {
        if (!this.is_complimentary) {
            this._complimentary_prev_discount = this.getDiscount();
            this.complimentary_value = Math.abs(Number(this.priceIncl || 0));
            this.setDiscount(100);
            this.is_complimentary = true;
            return;
        }

        this.setDiscount(Number(this._complimentary_prev_discount || 0));
        this.is_complimentary = false;
        this.complimentary_value = 0;
        this._complimentary_prev_discount = null;
    },
});

patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        ComplimentaryLineButton,
    },
});

patch(ControlButtons.prototype, {
    toggleComplimentaryOrderline() {
        const line = this.currentOrder?.getSelectedOrderline();
        if (!line) {
            return;
        }
        line.toggleComplimentary();
        this.render();
    },

    isSelectedLineComplimentary() {
        const line = this.currentOrder?.getSelectedOrderline();
        return Boolean(line && line.is_complimentary);
    },

    complimentaryButtonLabel() {
        return this.isSelectedLineComplimentary() ? _t("Remove Complimentary") : _t("Complimentary");
    },

    canToggleComplimentary() {
        return Boolean(this.currentOrder?.getSelectedOrderline());
    },
});
