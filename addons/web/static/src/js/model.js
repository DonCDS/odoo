odoo.define('web.Model', ['web.Class', 'web.session', 'web.pyeval'], function (require) {
    "use strict";

    var Class = require('web.Class'),
        session = require('web.session'),
        pyeval = require('web.pyeval');

    return Class.extend({
        /**
        new openerp.web.Model([session,] model_name[, context[, domain]])

        @constructs instance.web.Model
        @extends instance.web.Class
        
        @param {openerp.web.Session} [session] The session object used to communicate with
        the server.
        @param {String} model_name name of the OpenERP model this object is bound to
        @param {Object} [context]
        @param {Array} [domain]
        */
        init: function(name, context, domain) {
            this.name = name;
            this._context = context || {};
            this._domain = domain || [];
        },
        /**
         * @deprecated does not allow to specify kwargs, directly use call() instead
         */
        get_func: function (method_name) {
            var self = this;
            return function () {
                return self.call(method_name, _.toArray(arguments));
            };
        },
        /**
         * Call a method (over RPC) on the bound OpenERP model.
         *
         * @param {String} method name of the method to call
         * @param {Array} [args] positional arguments
         * @param {Object} [kwargs] keyword arguments
         * @param {Object} [options] additional options for the rpc() method
         * @returns {jQuery.Deferred<>} call result
         */
        call: function (method, args, kwargs, options) {
            args = args || [];
            kwargs = kwargs || {};
            if (!_.isArray(args)) {
                // call(method, kwargs)
                kwargs = args;
                args = [];
            }
            pyeval.ensure_evaluated(args, kwargs);
            var call_kw = '/web/dataset/call_kw/' + this.name + '/' + method;
            return session.rpc(call_kw, {
                model: this.name,
                method: method,
                args: args,
                kwargs: kwargs
            }, options);
        },
        /**
         * Executes a signal on the designated workflow, on the bound OpenERP model
         *
         * @param {Number} id workflow identifier
         * @param {String} signal signal to trigger on the workflow
         */
        exec_workflow: function (id, signal) {
            return session.rpc('/web/dataset/exec_workflow', {
                model: this.name,
                id: id,
                signal: signal
            });
        },
        call_button: function (method, args) {
            pyeval.ensure_evaluated(args, {});
            return session.rpc('/web/dataset/call_button', {
                model: this.name,
                method: method,
                // Should not be necessary anymore. Integrate remote in this?
                domain_id: null,
                context_id: args.length - 1,
                args: args || []
            });
        },
    });

});

odoo.define(['web.Model', 'web.data', 'web.session'], function (require) {
    "use strict";

    var Model = require('web.Model'),
        data = require('web.data'),
        session = require('web.session');
        
    Model.include({
        /**
         * Fetches a Query instance bound to this model, for searching
         *
         * @param {Array<String>} [fields] fields to ultimately fetch during the search
         * @returns {instance.web.Query}
         */
        query: function (fields) {
            return new data.Query(this, fields);
        },
        /**
         * Fetches the model's domain, combined with the provided domain if any
         *
         * @param {Array} [domain] to combine with the model's internal domain
         * @returns {instance.web.CompoundDomain} The model's internal domain, or the AND-ed union of the model's internal domain and the provided domain
         */
        domain: function (domain) {
            if (!domain) { return this._domain; }
            return new data.CompoundDomain(this._domain, domain);
        },
        /**
         * Fetches the combination of the user's context and the domain context,
         * combined with the provided context if any
         *
         * @param {Object} [context] to combine with the model's internal context
         * @returns {instance.web.CompoundContext} The union of the user's context and the model's internal context, as well as the provided context if any. In that order.
         */
        context: function (context) {
            return new data.CompoundContext(session.user_context, this._context, context || {});
        },
    });

});
