function odoo_website_forum_chrome_widget(website_forum_chrome) {
    //var QWeb = openerp.qweb,
    var QWeb = website_forum_chrome.qweb,
    _t = openerp._t;

    website_forum_chrome.website_forum_chrome_widget = openerp.Widget.extend({
        template: "WebsiteForumChrome",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$el.find(".o_submit_link").on('click', this.on_click_submit);
        },
        on_click_submit: function() {
            var is_jump = this.$el.find(".o_jump_page:checked");
            var url = this.$el.find('select').val();
            console.log("is_jump is ::: ", is_jump);
            if (is_jump.length) {
                console.log("document's current URL ", document.URL, url);
                alert("Stop");
                window.open(url);
            }
        },
    });

}