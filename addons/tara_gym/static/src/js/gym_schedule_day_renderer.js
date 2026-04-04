/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getColor } from "@web/views/calendar/utils";

const { DateTime } = luxon;
const START_HOUR = 0; // Starts from 00:00
const END_HOUR = 23;  // Ends at 23:59

export class GymScheduleDayRenderer extends Component {
    static template = "tara_gym.GymScheduleDayRenderer";
    static props = {
        model: Object,
        setDate: { type: Function, optional: true },
        createRecord: Function,
        editRecord: Function,
        deleteRecord: Function,
        isWeekendVisible: { type: Boolean, optional: true },
        callbackRecorder: { type: Object, optional: true },
        onSquareSelection: { type: Function, optional: true },
        cleanSquareSelection: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const hoursList = [];
        for (let i = START_HOUR; i <= END_HOUR; i++) {
            hoursList.push(`${i.toString().padStart(2, '0')}:00`);
            hoursList.push(`${i.toString().padStart(2, '0')}:30`);
        }

        this.state = useState({
            rooms: [],
            hours: hoursList,
            workingHours: {},
        });

        onWillStart(async () => {
            await this.fetchRooms();
        });
    }

    async fetchRooms() {
        // Fetch active rooms to use as columns
        const rooms = await this.orm.searchRead('gym.room', [], ['id', 'name', 'color', 'resource_calendar_id'], { order: 'id asc' });

        // Fetch working hours (attendance records) for any calendars used by these rooms
        const calendarIds = [...new Set(rooms.map(r => r.resource_calendar_id && r.resource_calendar_id[0]).filter(Boolean))];

        let attendances = [];
        if (calendarIds.length > 0) {
            // week day in Odoo: 0 = Mon, 1 = Tue ... 6 = Sun
            // luxon weekday: 1 = Mon ... 7 = Sun
            const odooDayOfWeek = (this.date.weekday - 1).toString();

            attendances = await this.orm.searchRead(
                'resource.calendar.attendance',
                [['calendar_id', 'in', calendarIds], ['dayofweek', '=', odooDayOfWeek]],
                ['calendar_id', 'hour_from', 'hour_to']
            );
        }

        // Map working hours per calendar
        const hoursByCalendar = {};
        for (const att of attendances) {
            const calId = att.calendar_id[0];
            if (!hoursByCalendar[calId]) {
                hoursByCalendar[calId] = [];
            }
            hoursByCalendar[calId].push({
                from: att.hour_from,
                to: att.hour_to
            });
        }

        this.state.rooms = rooms;
        this.state.workingHours = hoursByCalendar;
    }

    get date() {
        return this.props.model.date; // luxon DateTime
    }

    get formattedDate() {
        return this.date.toFormat("EEEE, d MMMM yyyy");
    }

    get eventsByRoom() {
        const records = Object.values(this.props.model.records);
        const grouped = {};

        for (const room of this.state.rooms) {
            grouped[room.id] = [];
        }
        grouped['unassigned'] = [];

        // Base values for positioning (px)
        const PIXELS_PER_MINUTE = 2; // 1 hour = 120px

        for (const record of records) {
            const rawRecord = record.rawRecord;
            const roomId = rawRecord.room_id ? rawRecord.room_id[0] : 'unassigned';

            // Odoo model records have `start` and `end` as luxon DateTime objects
            const start = record.start;
            const end = record.end || start.plus({ hours: 1 });

            // Limit bounds within today's view (7:00 to 22:00)
            const dayStart = this.date.set({ hour: START_HOUR, minute: 0, second: 0 });
            const dayEnd = this.date.set({ hour: END_HOUR, minute: 59, second: 59 });

            if (end < dayStart || start > dayEnd || record.isAllDay) {
                continue; // Outside of daily view range or allday
            }

            // Calculations
            let topMinutes = start.diff(dayStart, 'minutes').minutes;
            let durationMinutes = end.diff(start, 'minutes').minutes;

            if (topMinutes < 0) {
                durationMinutes += topMinutes;
                topMinutes = 0;
            }

            if (durationMinutes > 0) {
                const top = (topMinutes * PIXELS_PER_MINUTE) + 8; // Match the 8px CSS padding layout
                const height = durationMinutes * PIXELS_PER_MINUTE;

                let colorClass = "";
                let bgStyle = "";
                const colorVal = getColor(rawRecord.room_color || record.colorIndex);
                if (typeof colorVal === "number") {
                    colorClass = `o_calendar_color_${colorVal}`;
                } else if (typeof colorVal === "string") {
                    bgStyle = `background-color: ${colorVal};`;
                } else {
                    colorClass = "o_calendar_color_0";
                }

                const eventData = {
                    id: record.id,
                    title: rawRecord.name || record.display_name,
                    trainer: rawRecord.trainer_id ? rawRecord.trainer_id[1] : false,
                    type: rawRecord.booking_type === 'class' ? 'Class' : 'Service',
                    timeText: `${start.toFormat('HH:mm')} - ${end.toFormat('HH:mm')}`,
                    colorClass: colorClass,
                    bgStyle: bgStyle,
                    top: top,
                    height: Math.max(height, 20), // Minimum height
                    record: record,
                };

                if (grouped[roomId]) {
                    grouped[roomId].push(eventData);
                } else {
                    grouped['unassigned'].push(eventData);
                }
            }
        }

        return grouped;
    }

    isSlotAvailable(roomId, timeStr) {
        if (roomId === 'unassigned') return true;

        const room = this.state.rooms.find(r => r.id === roomId);
        if (!room || !room.resource_calendar_id) return true; // No working hours = always available

        const calId = room.resource_calendar_id[0];
        const attendances = this.state.workingHours[calId];

        if (!attendances || attendances.length === 0) return false; // No attendance for this day = closed

        const [hour, min] = timeStr.split(':').map(Number);
        const slotStartFloat = hour + (min / 60);

        return attendances.some(att => slotStartFloat >= att.from && slotStartFloat < att.to);
    }

    onClickTimeSlot(roomId, timeStr) {
        if (!this.isSlotAvailable(roomId, timeStr)) {
            return; // Block booking on unavailable slots
        }
        // timeStr is like "07:00" or "07:30"
        const [hour, min] = timeStr.split(':').map(Number);

        // Start date in user's timezone
        const start = this.date.set({ hour: hour, minute: min, second: 0 });
        const end = start.plus({ hours: 1 }); // Default to 1 hour duration

        // Convert to UTC for saving to DB correctly if needed, matching what Odoo Quick Create does.
        // Odoo's `createRecord` natively handles timezone conversion if fed correct UTC / localized strings based on fields,
        // but here we redirect to a wizard, so we provide default context values in UTC string format as server expects
        const context = {
            default_start_datetime: start.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"),
            default_end_datetime: end.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"),
        };

        if (roomId !== 'unassigned') {
            context.default_room_id = roomId;
        }
        console.log(context);

        this.action.doAction({
            name: "Create Booking",
            type: "ir.actions.act_window",
            res_model: "gym.schedule.create.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: context,
        }, {
            onClose: () => {
                this.props.model.load(); // Refresh calendar after wizard closes
            }
        });
    }

    onClickEvent(ev, evData) {
        ev.stopPropagation();
        this.props.editRecord(evData.record);
    }

    navigatePrevious() {
        if (this.props.setDate) {
            this.props.setDate('previous');
        }
    }

    navigateNext() {
        if (this.props.setDate) {
            this.props.setDate('next');
        }
    }

    navigateToday() {
        if (this.props.setDate) {
            this.props.setDate('today');
        }
    }
}
