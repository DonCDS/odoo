odoo.define('web.core', ['web.Class', 'web.mixins', 'web.Registry', 'qweb', '_', '$', 'web.translation'], function (require) {
"use strict";

var Class = require('web.Class'),
    Registry = require('web.Registry'),
    qweb = require('qweb'),
    _ = require('_'),
    $ = require('$'),
    translation = require('web.translation'),
    mixins = require('web.mixins');

var debug = $.deparam($.param.querystring()).debug !== undefined;

var _t = translation._t,
    _lt = translation._lt;

/**
 * Event Bus used to bind events scoped in the current instance
 */
var Bus = Class.extend(mixins.EventDispatcherMixin, {
    init: function() {
        mixins.EventDispatcherMixin.init.call(this, parent);
        var self = this;
        // TODO fme: allow user to bind keys for some global actions.
        //           check gtk bindings
        // http://unixpapa.com/js/key.html
        _.each('click,dblclick,keydown,keypress,keyup'.split(','), function(evtype) {
            $('html').on(evtype, function(ev) {
                self.trigger(evtype, ev);
            });
        });
        _.each('resize,scroll'.split(','), function(evtype) {
            $(window).on(evtype, function(ev) {
                self.trigger(evtype, ev);
            });
        });
    },
});

// Underscore customization
//-------------------------------------------------------------------------
_.str.toBoolElse = function (str, elseValues, trueValues, falseValues) {
    var ret = _.str.toBool(str, trueValues, falseValues);
    if (_.isUndefined(ret)) {
        return elseValues;
    }
    return ret;
};

// nvd3 customization
//-------------------------------------------------------------------------
nv.dev = false;  // sets nvd3 library in production mode

// monkey patch nvd3 to allow removing eventhandler on windowresize events
// see https://github.com/novus/nvd3/pull/396 for more details

// Adds a resize listener to the window.
nv.utils.onWindowResize = function(fun) {
    if (fun === null) return;
    window.addEventListener('resize', fun);
};

// Backwards compatibility with current API.
nv.utils.windowResize = nv.utils.onWindowResize;

// Removes a resize listener from the window.
nv.utils.offWindowResize = function(fun) {
    if (fun === null) return;
    window.removeEventListener('resize', fun);
};

// monkey patch nvd3 to prevent crashes when user changes view and nvd3 tries
// to remove tooltips after 500 ms...  seriously nvd3, what were you thinking?
nv.tooltip.cleanup = function () {
    $('.nvtooltip').remove();
};


// Bootstrap customization
//-------------------------------------------------------------------------
/* Bootstrap defaults overwrite */
$.fn.tooltip.Constructor.DEFAULTS.placement = 'auto top';
$.fn.tooltip.Constructor.DEFAULTS.html = true;
$.fn.tooltip.Constructor.DEFAULTS.trigger = 'hover focus click';
$.fn.tooltip.Constructor.DEFAULTS.container = 'body';
//overwrite bootstrap tooltip method to prevent showing 2 tooltip at the same time
var bootstrap_show_function = $.fn.tooltip.Constructor.prototype.show;
$.fn.modal.Constructor.prototype.enforceFocus = function () { };
$.fn.tooltip.Constructor.prototype.show = function () {
    $('.tooltip').remove();
    //the following fix the bug when using placement
    //auto and the parent element does not exist anymore resulting in
    //an error. This should be remove once we updade bootstrap to a version that fix the bug
    //edit: bug has been fixed here : https://github.com/twbs/bootstrap/pull/13752
    var e = $.Event('show.bs.' + this.type);
    var inDom = $.contains(document.documentElement, this.$element[0]);
    if (e.isDefaultPrevented() || !inDom) return;
    return bootstrap_show_function.call(this);
};

// IE patch.  I know that IE is not a library
//-------------------------------------------------------------------------
if (typeof(console) === "undefined") {
    // Even IE9 only exposes console object if debug window opened
    window.console = {};
    ('log error debug info warn assert clear dir dirxml trace group'
        + ' groupCollapsed groupEnd time timeEnd profile profileEnd count'
        + ' exception').split(/\s+/).forEach(function(property) {
            console[property] = _.identity;
    });
}

/**
    Some hack to make placeholders work in ie9.
*/
if (!('placeholder' in document.createElement('input'))) {    
    document.addEventListener("DOMNodeInserted",function(event){
        var nodename =  event.target.nodeName.toLowerCase();
        if ( nodename === "input" || nodename == "textarea" ) {
            $(event.target).placeholder();
        }
    });
}


// jquery customization
//-------------------------------------------------------------------------
jQuery.expr[":"].Contains = jQuery.expr.createPseudo(function(arg) {
    return function( elem ) {
        return jQuery(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
    };
});

/** Custom jQuery plugins */
$.fn.getAttributes = function() {
    var o = {};
    if (this.length) {
        for (var attr, i = 0, attrs = this[0].attributes, l = attrs.length; i < l; i++) {
            attr = attrs.item(i);
            o[attr.nodeName] = attr.value;
        }
    }
    return o;
};
$.fn.openerpClass = function(additionalClass) {
    // This plugin should be applied on top level elements
    additionalClass = additionalClass || '';
    if (!!$.browser.msie) {
        additionalClass += ' openerp_ie';
    }
    return this.each(function() {
        $(this).addClass('openerp ' + additionalClass);
    });
};
$.fn.openerpBounce = function() {
    return this.each(function() {
        $(this).css('box-sizing', 'content-box').effect('bounce', {distance: 18, times: 5}, 250);
    });
};

// jquery autocomplete tweak to allow html and classnames
var proto = $.ui.autocomplete.prototype,
    initSource = proto._initSource;

function filter( array, term ) {
    var matcher = new RegExp( $.ui.autocomplete.escapeRegex(term), "i" );
    return $.grep( array, function(value_) {
        return matcher.test( $( "<div>" ).html( value_.label || value_.value || value_ ).text() );
    });
}

$.extend( proto, {
    _initSource: function() {
        if ( this.options.html && $.isArray(this.options.source) ) {
            this.source = function( request, response ) {
                response( filter( this.options.source, request.term ) );
            };
        } else {
            initSource.call( this );
        }
    },

    _renderItem: function( ul, item) {
        return $( "<li></li>" )
            .data( "item.autocomplete", item )
            .append( $( "<a></a>" )[ this.options.html ? "html" : "text" ]( item.label ) )
            .appendTo( ul )
            .addClass(item.classname);
    }
});



/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template)
 *
 * Useful when defining translatable strings in code evaluated before the
 * translation database is loaded, as class attributes or at the top-level of
 * an OpenERP Web module
 *
 * @param {String} s string to translate
 * @returns {Object} lazy translation object
 */
qweb.debug = debug;
_.extend(qweb.default_dict, {
    '__debug__': debug,
    'moment': function(date) { return new moment(date); },
});

qweb.preprocess_node = function() {
    // Note that 'this' is the Qweb Node
    switch (this.node.nodeType) {
        case Node.TEXT_NODE:
        case Node.CDATA_SECTION_NODE:
            // Text and CDATAs
            var translation = this.node.parentNode.attributes['t-translation'];
            if (translation && translation.value === 'off') {
                return;
            }
            var match = /^(\s*)([\s\S]+?)(\s*)$/.exec(this.node.data);
            if (match) {
                this.node.data = match[1] + _t(match[2]) + match[3];
            }
            break;
        case Node.ELEMENT_NODE:
            // Element
            var attr, attrs = ['label', 'title', 'alt', 'placeholder'];
            while ((attr = attrs.pop())) {
                if (this.attributes[attr]) {
                    this.attributes[attr] = _t(this.attributes[attr]);
                }
            }
    }
};

/** Setup jQuery timeago */
/*
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
{
    _t('less than a minute ago');
    _t('about a minute ago');
    _t('%d minutes ago');
    _t('about an hour ago');
    _t('%d hours ago');
    _t('a day ago');
    _t('%d days ago');
    _t('about a month ago');
    _t('%d months ago');
    _t('about a year ago');
    _t('%d years ago');
}

$.async_when = function() {
    var async = false;
    var def = $.Deferred();
    $.when.apply($, arguments).done(function() {
        var args = arguments;
        var action = function() {
            def.resolve.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    }).fail(function() {
        var args = arguments;
        var action = function() {
            def.reject.apply(def, args);
        };
        if (async)
            action();
        else
            setTimeout(action, 0);
    });
    async = true;
    return def;
};

return {
    debug: debug,

    // core classes and functions
    Class: Class,
    mixins: mixins,
    bus: new Bus (),
    _t: _t,
    _lt: _lt,

    // registries
    view_registry: new Registry(),
    crash_registry: new Registry(),
    action_registry : new Registry(),
    form_widget_registry: new Registry(),
    form_tag_registry: new Registry(),
    form_custom_registry: new Registry(),
    list_widget_registry: new Registry(),
    search_widgets_registry: new Registry(),
    search_filters_registry: new Registry(),

    // libraries
    qweb: qweb,
    _: _,
    $: $,
    nv: nv,
    d3: d3,
    Backbone: Backbone,
    py: py,
    moment: moment,
};


});
