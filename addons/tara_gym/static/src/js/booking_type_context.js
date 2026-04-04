odoo.define('tara_gym.booking_type_context', function(require) {
    "use strict";
    var FormController = require('web.FormController');

    FormController.include({
        async beforeExecuteActionButton(clickParams) {
            // if the button provided a booking_type in its buttonContext, make
            // sure the in-memory record has that value *before* saving.  this
            // allows the subsequent create() call to see it in vals.
            if (clickParams?.buttonContext?.booking_type) {
                try {
                    await this.model.root.update({
                        booking_type: clickParams.buttonContext.booking_type,
                    });
                } catch (e) {
                    // ignore any errors, save will still work without the field
                    console.warn('failed to set booking_type on record', e);
                }
            }
            return this._super.apply(this, arguments);
        },
    });
});