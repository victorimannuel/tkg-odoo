odoo.define('tara_gym.auto_redirect', function(require) {
    "use strict";
    var FormErrorDialog = require('web.FormErrorDialog');

    FormErrorDialog.include({
        setup: function () {
            this._super.apply(this, arguments);
            if (this.props && this.props.data &&
                this.props.data.name === "odoo.exceptions.RedirectWarning" &&
                (!this.message || this.message === '')) {
                Promise.resolve().then(this.onRedirectBtnClicked.bind(this));
            }
        },
    });
});