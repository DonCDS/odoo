odoo.define('web.Loading', ['web.core', 'web.Widget', 'web.session', 'web.framework'], function (require) {
    "use strict";

    var core = require('web.core'),
        Widget = require('web.Widget'),
        session = require('web.session'),
        framework = require('web.framework');

    var _t = core._t;

    return Widget.extend({
        template: _t("Loading"),
        init: function(parent) {
            this._super(parent);
            this.count = 0;
            this.blocked_ui = false;
            session.on("request", this, this.request_call);
            session.on("response", this, this.response_call);
            session.on("response_failed", this, this.response_call);
        },
        destroy: function() {
            this.on_rpc_event(-this.count);
            this._super();
        },
        request_call: function() {
            this.on_rpc_event(1);
        },
        response_call: function() {
            this.on_rpc_event(-1);
        },
        on_rpc_event : function(increment) {
            var self = this;
            if (!this.count && increment === 1) {
                // Block UI after 3s
                this.long_running_timer = setTimeout(function () {
                    self.blocked_ui = true;
                    framework.blockUI();
                }, 3000);
            }

            this.count += increment;
            if (this.count > 0) {
                if (session.debug) {
                    this.$el.text(_.str.sprintf( _t("Loading (%d)"), this.count));
                } else {
                    this.$el.text(_t("Loading"));
                }
                this.$el.show();
                this.getParent().$el.addClass('oe_wait');
            } else {
                this.count = 0;
                clearTimeout(this.long_running_timer);
                // Don't unblock if blocked by somebody else
                if (self.blocked_ui) {
                    this.blocked_ui = false;
                    framework.unblockUI();
                }
                this.$el.fadeOut();
                this.getParent().$el.removeClass('oe_wait');
            }
        }
    });
});

odoo.define('web.ChangePassword', ['web.Widget', 'web.Dialog', 'web.core'], function (require) {
    "use strict";

    var Widget = require('web.Widget'),
        core = require('web.core'),
        Dialog = require('web.Dialog');

    var _t = core._t;

    var ChangePassword = Widget.extend({
        template: "ChangePassword",
        start: function() {
            var self = this;
            this.getParent().dialog_title = _t("Change Password");
            var $button = self.$el.find('.oe_form_button');
            $button.appendTo(this.getParent().$buttons);
            $button.eq(2).click(function(){
               self.$el.parents('.modal').modal('hide');
            });
            $button.eq(0).click(function(){
              self.rpc("/web/session/change_password",{
                   'fields': $("form[name=change_password_form]").serializeArray()
              }).done(function(result) {
                   if (result.error) {
                      self.display_error(result);
                      return;
                   } else {
                      self.do_action('logout');
                   }
              });
           });
        },
        display_error: function (error) {
            return new Dialog(this, {
                size: 'medium',
                title: error.title,
                buttons: [
                    {text: _t("Ok"), click: function() { this.parents('.modal').modal('hide'); }}
                ]
            }, $('<div>').html(error.error)).open();
        },
    });

    core.action_registry.add("change_password", ChangePassword);

    return ChangePassword;
});

odoo.define('web.Sidebar', ['web.core', 'web.Widget', 'web.Dialog', 'web.session', 'web.framework', 'web.pyeval', 'web.data'], function (require) {
    "use strict";

    var Widget = require('web.Widget'),
        Dialog = require('web.Dialog'),
        core = require('web.core'),
        pyeval = require('web.pyeval'),
        session = require('web.session'),
        framework = require('web.framework'),
        data = require('web.data');

    var QWeb = core.qweb,
        _t = core._t;

    return Widget.extend({
        init: function(parent) {
            var self = this;
            this._super(parent);
            this.sections = [
                { 'name' : 'print', 'label' : _t('Print'), },
                { 'name' : 'other', 'label' : _t('More'), }
            ];
            this.items = {
                'print' : [],
                'other' : []
            };
            this.fileupload_id = _.uniqueId('oe_fileupload');
            $(window).on(this.fileupload_id, function() {
                var args = [].slice.call(arguments).slice(1);
                self.do_attachement_update(self.dataset, self.model_id,args);
                framework.unblockUI();
            });
        },
        start: function() {
            var self = this;
            this._super(this);
            this.redraw();
            this.$el.on('click','.dropdown-menu li a', function(event) {
                var section = $(this).data('section');
                var index = $(this).data('index');
                var item = self.items[section][index];
                if (item.callback) {
                    item.callback.apply(self, [item]);
                } else if (item.action) {
                    self.on_item_action_clicked(item);
                } else if (item.url) {
                    return true;
                }
                event.preventDefault();
            });
        },
        redraw: function() {
            var self = this;
            self.$el.html(QWeb.render('Sidebar', {widget: self}));

            // Hides Sidebar sections when item list is empty
            this.$('.oe_form_dropdown_section').each(function() {
                $(this).toggle(!!$(this).find('li').length);
            });
            self.$("[title]").tooltip({
                delay: { show: 500, hide: 0}
            });
        },
        /**
         * For each item added to the section:
         *
         * ``label``
         *     will be used as the item's name in the sidebar, can be html
         *
         * ``action``
         *     descriptor for the action which will be executed, ``action`` and
         *     ``callback`` should be exclusive
         *
         * ``callback``
         *     function to call when the item is clicked in the sidebar, called
         *     with the item descriptor as its first argument (so information
         *     can be stored as additional keys on the object passed to
         *     ``add_items``)
         *
         * ``classname`` (optional)
         *     ``@class`` set on the sidebar serialization of the item
         *
         * ``title`` (optional)
         *     will be set as the item's ``@title`` (tooltip)
         *
         * @param {String} section_code
         * @param {Array<{label, action | callback[, classname][, title]}>} items
         */
        add_items: function(section_code, items) {
            if (items) {
                this.items[section_code].unshift.apply(this.items[section_code],items);
                this.redraw();
            }
        },
        add_toolbar: function(toolbar) {
            var self = this;
            _.each(['print','action','relate'], function(type) {
                var items = toolbar[type];
                if (items) {
                    for (var i = 0; i < items.length; i++) {
                        items[i] = {
                            label: items[i]['name'],
                            action: items[i],
                            classname: 'oe_sidebar_' + type
                        };
                    }
                    self.add_items(type=='print' ? 'print' : 'other', items);
                }
            });
        },
        on_item_action_clicked: function(item) {
            var self = this;
            self.getParent().sidebar_eval_context().done(function (sidebar_eval_context) {
                var ids = self.getParent().get_selected_ids();
                var domain;
                if (self.getParent().get_active_domain) {
                    domain = self.getParent().get_active_domain();
                }
                else {
                    domain = $.Deferred().resolve(undefined);
                }
                if (ids.length === 0) {
                    new Dialog(this, { title: _t("Warning"), size: 'medium',}, $("<div />").text(_t("You must choose at least one record."))).open();
                    return false;
                }
                var active_ids_context = {
                    active_id: ids[0],
                    active_ids: ids,
                    active_model: self.getParent().dataset.model,
                };

                $.when(domain).done(function (domain) {
                    if (domain !== undefined) {
                        active_ids_context.active_domain = domain;
                    }
                    var c = pyeval.eval('context',
                    new data.CompoundContext(
                        sidebar_eval_context, active_ids_context));

                    self.rpc("/web/action/load", {
                        action_id: item.action.id,
                        context: c
                    }).done(function(result) {
                        result.context = new data.CompoundContext(
                            result.context || {}, active_ids_context)
                                .set_eval_context(c);
                        result.flags = result.flags || {};
                        result.flags.new_window = true;
                        self.do_action(result, {
                            on_close: function() {
                                // reload view
                                self.getParent().reload();
                            },
                        });
                    });
                });
            });
        },
        do_attachement_update: function(dataset, model_id, args) {
            this.dataset = dataset;
            this.model_id = model_id;
            if (args && args[0].error) {
                this.do_warn(_t('Uploading Error'), args[0].error);
            }
            if (!model_id) {
                this.on_attachments_loaded([]);
            } else {
                var dom = [ ['res_model', '=', dataset.model], ['res_id', '=', model_id], ['type', 'in', ['binary', 'url']] ];
                var ds = new data.DataSetSearch(this, 'ir.attachment', dataset.get_context(), dom);
                ds.read_slice(['name', 'url', 'type', 'create_uid', 'create_date', 'write_uid', 'write_date'], {}).done(this.on_attachments_loaded);
            }
        },
        on_attachments_loaded: function(attachments) {
            var self = this;
            var prefix = session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'name'});
            _.each(attachments,function(a) {
                a.label = a.name;
                if(a.type === "binary") {
                    a.url = prefix  + '&id=' + a.id + '&t=' + (new Date().getTime());
                }
            });
            self.items.files = attachments;
            self.redraw();
            this.$('.oe_sidebar_add_attachment .oe_form_binary_file').change(this.on_attachment_changed);
            this.$el.find('.oe_sidebar_delete_item').click(this.on_attachment_delete);
        },
        on_attachment_changed: function(e) {
            var $e = $(e.target);
            if ($e.val() !== '') {
                this.$el.find('form.oe_form_binary_form').submit();
                $e.parent().find('input[type=file]').prop('disabled', true);
                $e.parent().find('button').prop('disabled', true).find('img, span').toggle();
                this.$('.oe_sidebar_add_attachment a').text(_t('Uploading...'));
                framework.blockUI();
            }
        },
        on_attachment_delete: function(e) {
            e.preventDefault();
            e.stopPropagation();
            var self = this;
            var $e = $(e.currentTarget);
            if (confirm(_t("Do you really want to delete this attachment ?"))) {
                (new data.DataSet(this, 'ir.attachment')).unlink([parseInt($e.attr('data-id'), 10)]).done(function() {
                    self.do_attachement_update(self.dataset, self.model_id);
                });
            }
        }
    });
});

odoo.define('web.Notification', ['web.Widget'], function (require) {
    "use strict";

    var Widget = require('web.Widget');

    return Widget.extend({
        template: 'Notification',
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$el.notify({
                speed: 500,
                expires: 2500
            });
        },
        notify: function(title, text, sticky) {
            sticky = !!sticky;
            var opts = {};
            if (sticky) {
                opts.expires = false;
            }
            return this.$el.notify('create', {
                title: title,
                text: text
            }, opts);
        },
        warn: function(title, text, sticky) {
            sticky = !!sticky;
            var opts = {};
            if (sticky) {
                opts.expires = false;
            }
            return this.$el.notify('create', 'oe_notification_alert', {
                title: title,
                text: text
            }, opts);
        }
    });
});

odoo.define('web.SystrayMenu', ['web.Widget'], function (require) {
    "use strict";

    var Widget = require('web.Widget');

    var SystrayMenu = Widget.extend({
        /**
         * This widget renders the systray menu. It creates and renders widgets
         * pushed in instance.web.SystrayItems.
         */
        init: function(parent) {
            this._super(parent);
            this.items = [];
            this.load = $.Deferred();
        },
        start: function() {
            var self = this;
            self._super.apply(this, arguments);
            self.load_items();
            return $.when.apply($, self.items).done(function () {
                self.load.resolve();
            });
        },
        load_items: function() {
            var self = this;
            _.each(SystrayMenu.Items, function(widgetCls) {
                var cur_systray_item = new widgetCls(self);
                self.items.push(cur_systray_item.appendTo(self.$el));
            });
        },
    });

    SystrayMenu.Items = [];

    return SystrayMenu;
});

odoo.define('web.datepicker', ['web.Widget', 'web.core', 'web.time_utils', 'web.formats'], function (require) {
    "use strict";

    var core = require('web.core'),
        Widget = require('web.Widget'),
        time_utils = require('web.time_utils'),
        formats = require('web.formats');

    var _t = core._t,
        moment = core.moment;

    var DateTimeWidget = Widget.extend({
        template: "web.datepicker",
        type_of_date: "datetime",
        events: {
            'dp.change .oe_datepicker_main': 'change_datetime',
            'dp.show .oe_datepicker_main': 'set_datetime_default',
            'keypress .oe_datepicker_master': 'change_datetime',
        },
        init: function(parent) {
            this._super(parent);
            this.name = parent.name;
        },
        start: function() {
            var l10n = _t.database.parameters;
            var options = {
                pickTime: true,
                useSeconds: true,
                startDate: moment({ y: 1900 }),
                endDate: moment().add(200, "y"),
                calendarWeeks: true,
                icons : {
                    time: 'fa fa-clock-o',
                    date: 'fa fa-calendar',
                    up: 'fa fa-chevron-up',
                    down: 'fa fa-chevron-down'
                   },
                language : moment.locale(),
                format : time_utils.strftime_to_moment_format(l10n.date_format +' '+ l10n.time_format),
            };
            this.$input = this.$el.find('input.oe_datepicker_master');
            if (this.type_of_date === 'date') {
                options.pickTime = false;
                options.useSeconds = false;
                options.format = time_utils.strftime_to_moment_format(l10n.date_format);
            }
            this.picker = this.$('.oe_datepicker_main').datetimepicker(options);
            this.set_readonly(false);
            this.set({'value': false});
        },
        set_value: function(value_) {
            this.set({'value': value_});
            this.$input.val(value_ ? this.format_client(value_) : '');
        },
        get_value: function() {
            return this.get('value');
        },
        set_value_from_ui_: function() {
            var value_ = this.$input.val() || false;
            this.set_value(this.parse_client(value_));
        },
        set_readonly: function(readonly) {
            this.readonly = readonly;
            this.$input.prop('readonly', this.readonly);
        },
        is_valid_: function() {
            var value_ = this.$input.val();
            if (value_ === "") {
                return true;
            } else {
                try {
                    this.parse_client(value_);
                    return true;
                } catch(e) {
                    return false;
                }
            }
        },
        parse_client: function(v) {
            return formats.parse_value(v, {"widget": this.type_of_date});
        },
        format_client: function(v) {
            return formats.format_value(v, {"widget": this.type_of_date});
        },
        set_datetime_default: function(){
            //when opening datetimepicker the date and time by default should be the one from
            //the input field if any or the current day otherwise
            if (this.type_of_date === 'datetime') {
                var value = moment().second(0);
                if (this.$input.val().length !== 0 && this.is_valid_()){
                    value = this.$input.val();
                }
                this.$('.oe_datepicker_main').data('DateTimePicker').setValue(value);
            }
        },
        change_datetime: function(e) {
            if ((e.type !== "keypress" || e.which === 13) && this.is_valid_()) {
                this.set_value_from_ui_();
                this.trigger("datetime_changed");
            }
        },
        commit_value: function () {
            this.change_datetime();
        },
    });

    var DateWidget = DateTimeWidget.extend({
        type_of_date: "date"
    });

    return {
        DateTimeWidget: DateTimeWidget,
        DateWidget: DateWidget,
    };
});
