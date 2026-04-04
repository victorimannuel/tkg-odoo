/** @odoo-module */

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(Navbar.prototype, {
    async onClickOpenMemberProfile() {
        window.open('/odoo/gym-members', '_self');
    }
});
