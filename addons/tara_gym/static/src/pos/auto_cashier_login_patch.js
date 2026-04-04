/** @odoo-module */

import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

function extractUserId(employee) {
    if (!employee) {
        return false;
    }
    const user = employee.user_id;
    if (!user) {
        return false;
    }
    if (Array.isArray(user)) {
        return user[0];
    }
    if (typeof user === "number") {
        return user;
    }
    if (typeof user === "object") {
        return user.id || false;
    }
    return false;
}

function getEmployees(pos) {
    if (!pos) {
        return [];
    }
    if (Array.isArray(pos.employees)) {
        return pos.employees;
    }
    if (pos.employees && typeof pos.employees === "object") {
        return Object.values(pos.employees);
    }
    if (pos.models && pos.models["hr.employee"] && Array.isArray(pos.models["hr.employee"])) {
        return pos.models["hr.employee"];
    }
    if (Array.isArray(pos.employee_ids)) {
        return pos.employee_ids;
    }
    return [];
}

function getCurrentUserId(ctx) {
    return (
        ctx?.env?.services?.user?.userId ||
        ctx?.pos?.user?.id ||
        window?.odoo?.session_info?.uid ||
        false
    );
}

async function loadAutoCashierPayload(ctx) {
    if (!ctx?.env?.services?.rpc) {
        return {};
    }
    try {
        return await ctx.env.services.rpc('/tara_gym/pos_auto_cashier_payload', {});
    } catch {
        return {};
    }
}

patch(LoginScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            this._autoSelectCashierByCurrentUser();
        });
    },

    async _autoSelectCashierByCurrentUser() {
        const payload = await loadAutoCashierPayload(this);
        if (!payload?.auto_cashier) {
            return;
        }

        const currentUserId = getCurrentUserId(this);
        const targetEmployeeId = payload.cashier_employee_id || false;
        if (!currentUserId && !targetEmployeeId) {
            return;
        }

        for (let attempt = 0; attempt < 20; attempt++) {
            const employees = getEmployees(this.pos);
            if (!employees.length) {
                await new Promise((resolve) => setTimeout(resolve, 300));
                continue;
            }

            // Do nothing if cashier already selected.
            if (typeof this.pos.get_cashier === "function" && this.pos.get_cashier()) {
                return;
            }

            let matched = false;
            if (targetEmployeeId) {
                matched = employees.find((employee) => employee && employee.id === targetEmployeeId);
            }
            if (!matched && currentUserId) {
                matched = employees.find(
                    (employee) => extractUserId(employee) === currentUserId
                );
            }
            if (!matched) {
                return;
            }

            if (typeof this.selectCashier === "function") {
                this.selectCashier(matched);
                return;
            }
            if (typeof this.selectEmployee === "function") {
                this.selectEmployee(matched);
                return;
            }
            if (typeof this.clickEmployee === "function") {
                this.clickEmployee(matched);
                return;
            }
            if (typeof this.pos.setCashier === "function") {
                this.pos.setCashier(matched);
                return;
            }
            if (typeof this.pos.set_cashier !== "function") {
                return;
            }
            this.pos.set_cashier(matched);
            if (typeof this.pos.closeScreen === "function") {
                this.pos.closeScreen();
            } else if (typeof this.back === "function") {
                this.back();
            }
            return;
        }
    },
});
