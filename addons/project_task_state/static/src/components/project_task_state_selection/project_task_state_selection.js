/** @odoo-module **/

import { ProjectTaskStateSelection } from "@project/components/project_task_state_selection/project_task_state_selection";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProjectTaskStateSelection.prototype, {
    setup() {
        super.setup(...arguments);
        this.icons["05_pending"] = "fa fa-lg fa-clock-o";
        this.colorIcons["05_pending"] = "text-warning";
        this.colorButton["05_pending"] = "btn-outline-warning";
        
        // Modify In Progress color to blue (info)
        this.icons["01_in_progress"] = "o_status bg-info";
        this.colorIcons["01_in_progress"] = "text-info";
        this.colorButton["01_in_progress"] = "btn-outline-info";

        // Modify Changes Requested to purple
        this.colorIcons["02_changes_requested"] = "text-purple";
        this.colorButton["02_changes_requested"] = "btn-outline-purple";
    },

    get options() {
        const labels = new Map(super.options);
        const states = ["1_canceled", "1_done"];
        const currentState = this.props.record.data[this.props.name];
        if (currentState != "04_waiting_normal") {
            states.unshift("01_in_progress", "02_changes_requested", "05_pending", "03_approved");
        }
        return states.map((state) => {
            if (state === "05_pending" && !labels.has(state)) {
                return [state, _t("Pending")];
            }
            return [state, labels.get(state) || state];
        });
    }
});
