odoo.define('web.framework', ['web.core', 'web.Widget', 'web.session', 'web.crash_manager', 'web.utils'], function (require) {
"use strict";

var core = require('web.core'),
    Widget = require('web.Widget'),
    utils = require('web.utils'),
    crash_manager = require('web.crash_manager'),
    session = require('web.session');

var _t = core._t,
    Spinner = window.Spinner;

var messages_by_seconds = function() {
    return [
        [0, _t("Loading...")],
        [20, _t("Still loading...")],
        [60, _t("Still loading...<br />Please be patient.")],
        [120, _t("Don't leave yet,<br />it's still loading...")],
        [300, _t("You may not believe it,<br />but the application is actually loading...")],
        [420, _t("Take a minute to get a coffee,<br />because it's loading...")],
        [3600, _t("Maybe you should consider reloading the application by pressing F5...")]
    ];
};

var Throbber = Widget.extend({
    template: "Throbber",
    start: function() {
        var opts = {
          lines: 13, // The number of lines to draw
          length: 7, // The length of each line
          width: 4, // The line thickness
          radius: 10, // The radius of the inner circle
          rotate: 0, // The rotation offset
          color: '#FFF', // #rgb or #rrggbb
          speed: 1, // Rounds per second
          trail: 60, // Afterglow percentage
          shadow: false, // Whether to render a shadow
          hwaccel: false, // Whether to use hardware acceleration
          className: 'spinner', // The CSS class to assign to the spinner
          zIndex: 2e9, // The z-index (defaults to 2000000000)
          top: 'auto', // Top position relative to parent in px
          left: 'auto' // Left position relative to parent in px
        };
        this.spin = new Spinner(opts).spin(this.$el[0]);
        this.start_time = new Date().getTime();
        this.act_message();
    },
    act_message: function() {
        var self = this;
        setTimeout(function() {
            if (self.isDestroyed())
                return;
            var seconds = (new Date().getTime() - self.start_time) / 1000;
            var mes;
            _.each(messages_by_seconds(), function(el) {
                if (seconds >= el[0])
                    mes = el[1];
            });
            self.$(".oe_throbber_message").html(mes);
            self.act_message();
        }, 1000);
    },
    destroy: function() {
        if (this.spin)
            this.spin.stop();
        this._super();
    },
});


// special tweak for the web client
var old_async_when = $.async_when;
$.async_when = function() {
    if (session.synch)
        return $.when.apply(this, arguments);
    else
        return old_async_when.apply(this, arguments);
};


/** Setup blockui */
if ($.blockUI) {
    $.blockUI.defaults.baseZ = 1100;
    $.blockUI.defaults.message = '<div class="openerp oe_blockui_spin_container" style="background-color: transparent;">';
    $.blockUI.defaults.css.border = '0';
    $.blockUI.defaults.css["background-color"] = '';
}


var throbbers = [];

function blockUI () {
    var tmp = $.blockUI.apply($, arguments);
    var throbber = new Throbber();
    throbbers.push(throbber);
    throbber.appendTo($(".oe_blockui_spin_container"));
    return tmp;
}

function unblockUI () {
    _.invoke(throbbers, 'destroy');
    throbbers = [];
    return $.unblockUI.apply($, arguments);
}

/**
 * Redirect to url by replacing window.location
 * If wait is true, sleep 1s and wait for the server i.e. after a restart.
 */
function redirect (url, wait) {
    // Dont display a dialog if some xmlhttprequest are in progress
    crash_manager.disable();

    var load = function() {
        var old = "" + window.location;
        var old_no_hash = old.split("#")[0];
        var url_no_hash = url.split("#")[0];
        location.assign(url);
        if (old_no_hash === url_no_hash) {
            location.reload(true);
        }
    };

    var wait_server = function() {
        session.rpc("/web/webclient/version_info", {}).done(load).fail(function() {
            setTimeout(wait_server, 250);
        });
    };

    if (wait) {
        setTimeout(wait_server, 1000);
    } else {
        load();
    }
}

/**
 * Performs a fields_view_get and apply postprocessing.
 * return a {$.Deferred} resolved with the fvg
 *
 * @param {Object} args
 * @param {String|Object} args.model instance.web.Model instance or string repr of the model
 * @param {Object} [args.context] context if args.model is a string
 * @param {Number} [args.view_id] id of the view to be loaded, default view if null
 * @param {String} [args.view_type] type of view to be loaded if view_id is null
 * @param {Boolean} [args.toolbar=false] get the toolbar definition
 */
function fields_view_get (args) {
    function postprocess(fvg) {
        var doc = $.parseXML(fvg.arch).documentElement;
        fvg.arch = utils.xml_to_json(doc, (doc.nodeName.toLowerCase() !== 'kanban'));
        if ('id' in fvg.fields) {
            // Special case for id's
            var id_field = fvg.fields.id;
            id_field.original_type = id_field.type;
            id_field.type = 'id';
        }
        _.each(fvg.fields, function(field) {
            _.each(field.views || {}, function(view) {
                postprocess(view);
            });
        });
        return fvg;
    }
    return args.model.call('fields_view_get', {
        view_id: args.view_id,
        view_type: args.view_type,
        context: args.context,
        toolbar: args.toolbar || false
    }).then(postprocess);
}


//  * Client action to reload the whole interface.
//  * If params.menu_id, it opens the given menu entry.
//  * If params.wait, reload will wait the openerp server to be reachable before reloading
 
function Reload(parent, action) {
    var params = action.params || {};
    var menu_id = params.menu_id || false;
    var l = window.location;

    var sobj = $.deparam(l.search.substr(1));
    if (params.url_search) {
        sobj = _.extend(sobj, params.url_search);
    }
    var search = '?' + $.param(sobj);

    var hash = l.hash;
    if (menu_id) {
        hash = "#menu_id=" + menu_id;
    }
    var url = l.protocol + "//" + l.host + l.pathname + search + hash;

    redirect(url, params.wait);
}

core.action_registry.add("reload", Reload);


/**
 * Client action to go back home.
 */
function Home (parent, action) {
    var url = '/' + (window.location.search || '');
    redirect(url, action && action.params && action.params.wait);
}
core.action_registry.add("home", Home);

/**
 * Client action to go back in breadcrumb history.
 * If can't go back in history stack, will go back to home.
 */
function HistoryBack (parent) {
    parent.history_back().fail(function () {
        Home(parent);
    });
}
core.action_registry.add("history_back", HistoryBack);

function login() {
    redirect('/web/login');
}
core.action_registry.add("login", login);

function logout() {
    redirect('/web/session/logout');
}
core.action_registry.add("logout", logout);

/**
 * Client action to refresh the session context (making sure
 * HTTP requests will have the right one) then reload the
 * whole interface.
 */
function ReloadContext (parent, action) {
    // side-effect of get_session_info is to refresh the session context
    session.rpc("/web/session/get_session_info", {}).then(function() {
        Reload(parent, action);
    });
}
core.action_registry.add("reload_context", ReloadContext);


return {
    blockUI: blockUI,
    unblockUI: unblockUI,
    redirect: redirect,
    fields_view_get: fields_view_get,
};

});

