(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options.mailing_list_subscribe = website.snippet.Option.extend({
        choose_mailing_list: function (type, value) {
            var self = this;
            if (type !== "click") return;
            return website.prompt({
                id: "editor_new_mailing_list_subscribe_button",
                window_title: _t("Add a Newsletter Subscribe Button"),
                select: _t("Newsletter"),
                init: function (field) {
                    return website.session.model('mail.mass_mailing.list')
                            .call('name_search', ['', []], { context: website.get_context() });
                },
            }).then(function (mailing_list_id) {
                self.$target.attr("data-list-id", mailing_list_id);
            });
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.choose_mailing_list('click').fail(function () {
                self.editor.on_remove();
            });
        },
        clean_for_save: function () {
            this.$target.addClass("hidden");
        },
    });

    website.snippet.options.banner_popup = website.snippet.Option.extend({
        select_mailing_list: function (type, value) {
            var self = this;
            if (type !== "click") return;
            return website.prompt({
                id: "editor_new_mailing_list_subscribe_popup",
                window_title: _t("Add a Newsletter Subscribe Popup"),
                select: _t("Newsletter"),
                init: function (field) {
                    return website.session.model('mail.mass_mailing.list')
                            .call('name_search', ['', []]);
                },
            }).then(function (mailing_list_id) {
                openerp.jsonRpc('/web/dataset/call', 'call', {
                    model: 'mail.mass_mailing.list',
                    method: 'read',
                    args: [[parseInt(mailing_list_id)], ['popup_content'], website.get_context()],
                }).then(function (data) {
                    self.$target.find(".o_popup_content_dev").empty();
                    if (data && data[0].popup_content) {
                        $(data[0].popup_content).appendTo(self.$target.find(".o_popup_content_dev"))
                    }
                });
                self.$target.attr("data-list-id", mailing_list_id);
            });
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.select_mailing_list('click').fail(function () {
                self.editor.on_remove($.Event( "click" ));
            });
        },
    });

    website.EditorBar.include({
            edit: function () {
                var self = this;
                this._super();
                $('body').on('click','#edit_dialog',_.bind(this.edit_dialog, self.rte.editor));
            },
            save : function() {
                var $target = $('#wrapwrap').find('#banner_popup')
                $target.modal('hide')
                $target.css("display", "none")
                if ($target.length && !$target.find('.o_popup_content_dev').length) {
                    $target.find('.o_popup_modal_body').before($('<div class="o_popup_content_dev" data-oe-placeholder="Type Here ..."></div>')) }
                var res = this._super();
                if ($target && $target.length) {
                    var content = $('#wrapwrap .o_popup_content_dev').html()
                    if (!$('#wrapwrap').find('.o_popup_content_dev').children().length ) {
                        content = '<div data-oe-placeholder="Type Here ...">' + content + '</div>'
                    }
                    openerp.jsonRpc('/web/dataset/call', 'call', {
                        model: 'mail.mass_mailing.list',
                        method: 'write',
                        args: [$('#wrapwrap').find('.banner_popup').data('list-id'),
                           {'popup_content':content} || null,
                           website.get_context()],
                    });
                }
                return res;
            },
            edit_dialog : function() {
                $('#wrapwrap').find('#banner_popup').modal('show')
                $('.modal-backdrop').css("z-index", "0")
            },
        });
})();


