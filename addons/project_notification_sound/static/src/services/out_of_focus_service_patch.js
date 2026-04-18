/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";

patch(OutOfFocusService.prototype, {
    async notify(message, thread) {
        // Let the original notification popup show normally
        await super.notify(message, thread);
        
        // If it's a project task, force play the notification sound
        if (message.thread?.model === "project.task") {
            this._playSound();
        }
    }
});
