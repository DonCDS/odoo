(function() {

    "use strict";

    var instance = openerp,
        _t = instance.web._t;

    var QWeb = instance.web.qweb;
    instance.web.dashboard = {};

    instance.web.dashboard.Dashboard = instance.web.Widget.extend({
        template: 'DashboardMain',
        events: {
            'click .install_new_apps': 'new_apps',
        },
        start:function(){
            var self = this;
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.model.data',
                method: 'xmlid_to_res_id',
                args: ['base.view_users_form'],
            }).then(function(res_id) {
                self.user_form_id = res_id;
                self.load();
            });
        },
        load:function(){
            var self = this;
            openerp.jsonRpc("/dashboard/info", 'call', {}).then(function (data) {
                self.$el.find('#apps').append(QWeb.render("DashboardApps", data));
                new openerp.web.dashboard.DashboardInvitations(self,data).appendTo('#invitations');
                new openerp.web.dashboard.DashboardPlanner(self,data).appendTo('#planner');
                new openerp.web.dashboard.DashboardVideos(self,data).appendTo('#videos');
            });
        },
        new_apps:function(){
            this.do_action('base.open_module_tree', { 
                'additional_context': {'search_default_app':1,'search_default_not_installed':1}
            });
        },
        do_reload:function(){
            this.$el.find('.col > div').children().remove();
            this.load();
            $('.loader').addClass("hidden");
        },
        show_loading:function(message){
            $('.loader .text').text(_t(message));
            $('.loader').removeClass('hidden');
        }
    });

    instance.web.dashboard.DashboardInvitations = instance.web.Widget.extend({
        template: 'DashboardInvitations',
        events: {
            'click .send_invitations': 'send_invitations',
            'click .optional_message_toggler': 'optional_message_toggler',
            'click .user': 'on_user_clicked',
        },
        init: function(parent, data){
            this.data = data;
            this.parent = parent;
            this.user_form_id = this.parent.user_form_id;
            return this._super.apply(this, arguments);
        },
        send_invitations:function(e){
            var self = this;
            var $target = $(e.currentTarget);
            var user_emails = this.$el.find('#user_emails').val();
            var optional_message = this.$el.find('#optional_message').val();
            if(user_emails){
                self.parent.show_loading("Sending Invitations");
                $target.prop('disabled',true);
                $target.find('i.fa-cog').removeClass('hidden');
                openerp.jsonRpc("/dashboard/create_users", 'call', {
                    'users': user_emails,
                    'optional_message': optional_message
                })
                .then(function (data) {
                    $('.loader').addClass("hidden");
                    if(data.has_error){
                        self.do_warn(data.message,"");
                        $target.find('i.fa-cog').addClass('hidden');
                        $target.attr('disabled',false);
                    }else{
                        self.parent.do_reload();
                    }
                });
            }else{
                this.do_warn(_t("Please enter email addresses"),"");
            }

        },
        on_user_clicked: function (event) {
            // event.preventDefault();
            var user_id = $(event.target).data('user-id');

            var action = {
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: 'res.users',
                views: [[this.user_form_id, 'form']],
                res_id: user_id,
            }
            this.do_action(action);
        },
        optional_message_toggler:function(){
            this.$el.find('.optional_message_toggler').remove();
            this.$el.find('textarea.optional_message').slideToggle("fast");
        }

    });

    instance.web.dashboard.DashboardPlanner = openerp.planner.PlannerLauncher.extend({
        template: 'DashboardPlanner',
         events: {
            'click .proress_title,.progress': 'setup',
        },
        init: function(parent, data){
            this.data = data;
            this.parent = parent;
            return this._super.apply(this, arguments);
        },
        start: function() {
            var self = this;
            return self.fetch_application_planner().done(function(apps) {
                self.planner_apps = apps;
                return apps;
            });
        },
        setup: function(e){
            var self = this;
            this.planner = planner;
            var menu_id = $(e.currentTarget).attr('data-menu-id');
            this.planner = self.planner_by_menu[menu_id];
            this.dialog = new instance.planner.PlannerDialog(this.parent, this.planner);
            this.dialog.appendTo(document.body);
            this.dialog.$('#PlannerModal').modal('toggle');
            this.dialog.on("hide.bs.modal", self, function(percent){
                    self.parent.do_reload();
                });
        },
    });

    instance.web.dashboard.DashboardVideos = instance.web.Widget.extend({
        template: 'DashboardVideos',
         events: {
            'click .tw_share': 'tw',
            'click .fb_share': 'fb',
            'click .li_share': 'li',
        },
        init: function(parent, data){
            this.data = data;
            this.parent = parent;
            this.share_url = 'https://www.odoo.com/';
            this.share_text = encodeURIComponent("I'm using Odoo, an Open-Source Web App that manages my Sales, Projects, Accounting, Website, Warehouse, Shop..and so much more! #imusingodoo");
            //To-do: add video text and url's here
            this.video_urls = {
                'tw':[{'name':"#1 Lorem ipsum dolor sit amet",'url':'#hh'},{'name':"#2 Lorem ipsum dolor sit amet",'url':'#'},{'name':"#3 Lorem ipsum dolor sit amet",'url':'#'}],
                'fb':[{'name':"#4 Lorem ipsum dolor sit amet",'url':'#'},{'name':"#5 Lorem ipsum dolor sit amet",'url':'#'},{'name':"#6 Lorem ipsum dolor sit amet",'url':'#'}],
                'li':[{'name':"#7 Lorem ipsum dolor sit amet",'url':'#'},{'name':"#8 Lorem ipsum dolor sit amet",'url':'#'},{'name':"#9 Lorem ipsum dolor sit amet",'url':'#'}],
            };
            return this._super.apply(this, arguments);
        },
        tw:function(){
            var self =this;
            var win = window.open(
                  ['https://twitter.com/intent/tweet?tw_p=tweetbutton','&text=', self.share_text].join(''),
                  'twitter-share-dialog', 
                  'width=626,height=436');
            var closeCallback = function(e){
                if(e && e.data){
                    var data;
                    try{
                        data = JSON.parse(e.data);
                    }catch(e){
                        // Don't care.
                    }
                    if(data && data.params && data.params.indexOf('tweet') > -1){
                        self.load_videos('twitter');
                    }
                }
            };
            window.addEventListener ? window.addEventListener("message", closeCallback, !1) : window.attachEvent("onmessage", closeCallback)
        },
        fb:function(){
            var count_url = "http://graph.facebook.com/"+this.share_url;
            var popup_url = 'https://www.facebook.com/sharer/sharer.php?u='+encodeURIComponent(this.share_url);
            this.sharer(count_url, popup_url,'shares',10, 'facebook');
            
        },
        li:function(){
            var count_url = "https://www.linkedin.com/countserv/count/share?url="+ this.share_url + "&format=jsonp&callback=?";
            var popup_url = ['http://www.linkedin.com/shareArticle?mini=true&url=',this.share_url,'&title=','I am using odoo' ,'&summary=',this.share_text,'&source=','www.odoo.com'].join("");
            this.sharer(count_url, popup_url, 'count', 5500, 'linkedin');
        },
        sharer:function(count_url, popup_url, key, delay, network){
            var self = this;
            var share_count;
            var attempt = 0;
            self.parent.show_loading("Working");
            function closeCallback(){
                setTimeout(function(){
                    attempt = attempt+1;
                    $.getJSON(count_url, function( data ) {
                        if(share_count < data[key]){
                            self.load_videos(network);
                        }else{
                            if(attempt <= 3){
                                closeCallback();
                                self.parent.show_loading("Checking in "+network+" servers");
                            }else{   
                                self.do_warn(_t("Please share Odoo's awesomeness!"),"");
                                $('.loader').addClass("hidden");
                            }
                        }
                    });
                }, delay);
            };
            $.getJSON(count_url, function( data ) {
                share_count = data[key];
                var win = window.open(
                  popup_url, 
                  'Share Dialog', 
                  'width=626,height=436');
                var interval = window.setInterval(function() {
                try {
                        if (win == null || win.closed) {
                            window.clearInterval(interval);
                            closeCallback();
                        }
                     }
                catch (e) {
                    }
                }, 1000);
            });
        },
        load_videos:function(network){
            var self = this;
            openerp.jsonRpc("/dashboard/grant_videos", 'call', {'network':['dashboard.',network].join("")})
            .then(function (data) {
                self.parent.do_reload();
            });
        }
    });
    instance.web.client_actions.add('web_dashboard.main', 'instance.web.dashboard.Dashboard');
})();
