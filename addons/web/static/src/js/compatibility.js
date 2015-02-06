// ------------------------------------------------------------------------------
// Compatibility with Odoo v8.  
// 
// With the new module system, no global variable can (and should) be accessed
// in openerp.  This file exports everything, to mimic the previous global 
// namespace structure.  This is only supposed to be used by 3rd parties to 
// facilitate migration.  Odoo addons should not use the 'openerp' variable at 
// all.
// ------------------------------------------------------------------------------
odoo.define('web.compatibility', [
    'web.ActionManager',
    'web.core', 
    'web.data', 
    'web.FavoriteMenu',
    'web.form_common', 
    'web.form_relational',
    'web.form_widgets',
    'web.formats',
    'web.FormView',
    'web.ListView',
    'web.Menu', 
    'web.Model', 
    'web.pyeval',
    'web.Registry',
    'web.SearchView',
    'web.session',
    'web.Sidebar',
    'web.SystrayMenu', 
    'web.time_utils',
    'web.UserMenu', 
    'web.utils',
    'web.View',
    'web.ViewManager',
    'web.WebClient', 
    'web.Widget', 
    ], 
    function (require) {
"use strict";

var ActionManager = require('web.ActionManager'),
    core = require('web.core'),
    data = require('web.data'),
    FavoriteMenu = require('web.FavoriteMenu'),
    form_common = require('web.form_common'),
    formats = require('web.formats'),
    FormView = require('web.FormView'),
    form_relational = require('web.form_relational'), // necessary 
    form_widgets = require('web.form_widgets'), // necessary to be able to export them
    ListView = require('web.ListView'),
    Menu = require('web.Menu'),
    Model = require('web.Model'),
    pyeval = require('web.pyeval'),
    Registry = require('web.Registry'),
    SearchView = require('web.SearchView'),
    session = require('web.session'),
    Sidebar = require('web.Sidebar'),
    SystrayMenu = require('web.SystrayMenu'),
    time_utils = require('web.time_utils'),
    UserMenu = require('web.UserMenu'),
    utils = require('web.utils'),
    View = require('web.View'),
    ViewManager = require('web.ViewManager'),
    WebClient = require('web.WebClient'),
    Widget = require('web.Widget');

var client_started = $.Deferred();

var OldRegistry = Registry.extend({
    add: function (key, path) {
    },
    get_object: function (key) {
        return get_object(this.map[key]);
    },
});

openerp = openerp || {};

$.Mutex = utils.Mutex;
openerp._session_id = "instance0";
openerp._t = core._t;
openerp.get_cookie = utils.get_cookie;

openerp.qweb = core.qweb;
openerp.session = session;

openerp.web = openerp.web || {};
openerp.web._t = core._t;
openerp.web._lt = core._lt;

openerp.web.ActionManager = ActionManager;
openerp.web.auto_str_to_date = time_utils.auto_str_to_date;
openerp.web.BufferedDataSet = data.BufferedDataSet;
openerp.web.bus = core.bus;
openerp.web.Class = core.Class;
openerp.web.client_actions = make_old_registry(core.action_registry);
openerp.web.CompoundContext = data.CompoundContext;
openerp.web.CompoundDomain = data.CompoundDomain;
openerp.web.DataSetSearch = data.DataSetSearch;
openerp.web.DataSet = data.DataSet;
openerp.web.date_to_str = time_utils.date_to_str;

openerp.web.form = openerp.web.form || {};
openerp.web.form.AbstractField = form_common.AbstractField;
openerp.web.form.compute_domain = data.compute_domain;
openerp.web.form.DefaultFieldManager = form_common.DefaultFieldManager;
openerp.web.form.FieldChar = core.form_widget_registry.get('char');
openerp.web.form.FieldFloat = core.form_widget_registry.get('float');
openerp.web.form.FieldStatus = core.form_widget_registry.get('statusbar');
openerp.web.form.FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');
openerp.web.form.FieldMany2One = core.form_widget_registry.get('many2one');
openerp.web.form.FormWidget = form_common.FormWidget;
openerp.web.form.tags = make_old_registry(core.form_tag_registry);
openerp.web.form.widgets = make_old_registry(core.form_widget_registry);

openerp.web.format_value = formats.format_value;
openerp.web.FormView = FormView;

openerp.web.json_node_to_xml = utils.json_node_to_xml;

openerp.web.ListView = ListView;
openerp.web.Menu = Menu;
openerp.web.Model = Model;
openerp.web.normalize_format = time_utils.strftime_to_moment_format;
openerp.web.py_eval = pyeval.py_eval;
openerp.web.pyeval = pyeval;
openerp.web.qweb = core.qweb;

openerp.web.Registry = OldRegistry;

openerp.web.search = {};
openerp.web.search.FavoriteMenu = FavoriteMenu;
openerp.web.SearchView = SearchView;
openerp.web.Sidebar = Sidebar;
openerp.web.str_to_datetime = time_utils.str_to_datetime;
openerp.web.SystrayItems = SystrayMenu.Items;
openerp.web.UserMenu = UserMenu;
openerp.web.View = View;
openerp.web.ViewManager = ViewManager;
openerp.web.views = make_old_registry(core.view_registry);
openerp.web.WebClient = WebClient;
openerp.web.Widget = Widget;

openerp.Widget = openerp.web.Widget;
openerp.Widget.prototype.session = session;


WebClient.include({
    init: function () {
        openerp.client = this;
        openerp.webclient = this;
        start_modules();
        client_started.resolve();
        this._super.apply(this, arguments);
    },
});


function make_old_registry(registry) {
    return {
        add: function (key, path) {
            client_started.done(function () {
                registry.add(key, get_object(path));
            });
        },
    };
}
function get_object(path) {
    var object_match = openerp;
    path = path.split('.');
    // ignore first section
    for(var i=1; i<path.length; ++i) {
        object_match = object_match[path[i]];
    }
    return object_match;
}

/**
 * OpenERP instance constructor
 *
 * @param {Array|String} modules list of modules to initialize
 */
var inited = false;
function start_modules (modules) {
    if (modules === undefined) {
        modules = odoo._modules;
    }
    modules = _.without(modules, "web");
    if (inited) {
        throw new Error("OpenERP was already inited");
    }
    inited = true;
    for(var i=0; i < modules.length; i++) {
        var fct = openerp[modules[i]];
        if (typeof(fct) === "function") {
            openerp[modules[i]] = {};
            for (var k in fct) {
                openerp[modules[i]][k] = fct[k];
            }
            fct(openerp, openerp[modules[i]]);
        }
    }
    openerp._modules = ['web'].concat(modules);
    return openerp;
};

/**
    A class containing common utility methods useful when working with OpenERP as well as the PropertiesMixin.
*/
// openerp.web.Controller = Class.extend(mixins.PropertiesMixin, ControllerMixin, {
//     *
//      * Constructs the object and sets its parent if a parent is given.
//      *
//      * @param {openerp.web.Controller} parent Binds the current instance to the given Controller instance.
//      * When that controller is destroyed by calling destroy(), the current instance will be
//      * destroyed too. Can be null.
     
//     init: function(parent) {
//         mixins.PropertiesMixin.init.call(this);
//         this.setParent(parent);
//         this.session = openerp.session;
//     },
// });

// openerp.web.Query = data.Query;

});