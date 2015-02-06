odoo.define(['mail.mail', 'web.core'], function (require) {
    var mail = require('mail.mail'),
        core = require('web.core');

    mail.Thread.include({
        message_fetch: function() {
            return this._super.apply(this, arguments).done(function() {
                core.bus.trigger('chatter_messages_fetched');
            });
        }
    });    
});

