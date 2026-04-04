/** @odoo-module */

import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { GymScheduleDayRenderer } from "./gym_schedule_day_renderer";
import { registry } from "@web/core/registry";

class GymScheduleCalendarController extends CalendarController {
    /**
     * Override createRecord to open the schedule create wizard
     * instead of trying to create a gym.schedule record (SQL view).
     */
    createRecord(record) {
        const rawRecord = this.model.buildRawRecord(record);
        const context = this.model.makeContextDefaults(rawRecord);

        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "gym.schedule.create.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: context,
        });
    }
}

class GymScheduleCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: GymScheduleDayRenderer,
    };
}

registry.category("views").add("gym_schedule_calendar", {
    ...calendarView,
    Controller: GymScheduleCalendarController,
    Renderer: GymScheduleCalendarRenderer,
});
