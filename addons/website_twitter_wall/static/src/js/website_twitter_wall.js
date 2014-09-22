$(document).ready(function() {
    if($("#APIConf") != null)
        $("#APIConf").modal();
    
    $(".upload_bg_image").change(function(ev){
        var type =  $(this).attr("data-type");
        var id = $(this).attr("data-id");
        $('#back_img').ajaxSubmit({
            data: {
                id: id,
            },
            success: function(data){
                if(type == 'wall'){
                    $("div.full_screen")
                        .animate({opacity: 0.2}, '1500', 
                        function() {
                                $("div.full_screen").css({'background-image': 'url("data:image/jpg;base64,' + data + '")'})
                                .animate({opacity: 1}, '2500');
                        });
                }
            }
        });
    });
    
    if($("div[name='tweets_for_admin']").length){
        var $el = $("div[name='tweets_for_admin']").find(".wall_box");
        var twitter_wall = new openerp.website.twitter_walls($el);
        twitter_wall.start();
    }
    if($("div[name='tweets_for_client']").length){
        var twitter_wall = new openerp.website.tweet_wall($("#tweet_wall_div"), parseInt($("[wall_id]").attr("wall_id")));
        twitter_wall.start();
    }
    if($("div[name='tweets_for_archieve']").length){
        var $el = $("div[name='tweets_for_archieve']");
        var twitter_wall = new openerp.website.approve_tweet($("#approve_tweet_wall"), parseInt($el.attr("wall_id")));
        twitter_wall.start();
    }
});

var website = openerp.website;
openerp.website.twitter_walls = openerp.Class.extend({
    init: function($el){
        this.$el = $el;
    },
    start: function(){
        var self = this;
        this.bind_streaming();
        this.bind_view_mode();
    },
    
    //For Start and Stop Streaming
    bind_streaming: function(){
        var self = this;
        var $start_stop_button = self.$el.find(".btn-group button");
        $start_stop_button.click(function(){
            var value = $(this).attr("value");
            var wall_id = parseInt($(this).attr("wall_id"));
            $button = $(this); 
            openerp.jsonRpc("/tweet_moderate/streaming", 'call', {'wall_id' : wall_id, 'state' : value}).done(function(state) {
                $button.removeClass('stop_streaming start_streaming');
                if(state == 'startstreaming'){
                    $button.html("<i class=\"fa fa-refresh\"></i>")
                                 .attr("value", "stopstreaming")
                                 .addClass('stop_streaming btn-danger').removeClass('btn-success');
                    return;
                }
                $button.html("<i class=\"fa fa-refresh\"></i>")
                                .attr("value", "startstreaming")
                                .addClass('start_streaming btn-success').removeClass('btn-danger');
                
            }).fail(function(){self.error();});
        });
    },
    
    //For View Mode Change
    bind_view_mode: function(){
        var self = this;
        var $view_mode = self.$el.find("div.btn-group label");
        $view_mode.click(function(){
            var value = $(this).find("input").attr("value");
            var wall_id = parseInt($(this).attr("wall_id"));
            openerp.jsonRpc("/tweet_moderate/view_mode", 'call', {'wall_id' : wall_id, 'view_mode' : value}).done(function() {
            }).fail(function(){self.error();});
        });
    },
    
    error: function(){
        alert("Unable to reach Server");
    },

});

openerp.website.approve_tweet = openerp.Class.extend({
    template : 'twitter_tweets_list_mode',
    init : function($el, wall_id) {
        this.$el = $el;
        this.wall_id = wall_id;
        this.last_publish_date;
        this.limit = 5;
        this.last_tweet_id;
    },
    
    start: function(){
        var self = this;
        self.bind_scroll();
        self.get_data();
        self.animate_tweet();
    },
    
    get_data: function(){
        var self = this;
        return openerp.jsonRpc("/twitter_wall_tweet_data", 'call', {'wall_id' : self.wall_id, 'limit' : self.limit, 'last_tweet': self.last_tweet_id}).done(function(tweets) {
            if (tweets.length){
                tweets.forEach(function(tweet){
                    str = tweet['tweet'];
                    var url_pattern = /(\b(https?):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gi;
                    str = str.replace(url_pattern, '<span class="tweet_url_hash_highlight">$1</span>');
                    
                    var hash_pattern = /(\B#\w*[a-zA-Z]+\w*)/gi;
                    str = str.replace(hash_pattern, '<span class="tweet_url_hash_highlight">$1</span>');
                    
                    var uname_pattern = /(\B@\w*[a-zA-Z]+\w*)/gi;
                    str = str.replace(uname_pattern, '<span class="tweet_url_hash_highlight">$1</span>');
                    tweet['tweet'] = str;
                    self.animate_tweet(openerp.qweb.render("twitter_tweets_"+ self.$el.attr("view_mode"), {'res' : tweet}));
                });
                self.last_tweet_id = tweets[tweets.length -1].id;
            }
        });
    },
    
    bind_scroll: function(){
        var self = this;
        $(window).scroll(function(){
            if ($(window).scrollTop()  >= $(document).height() - 50 - $(window).height()){
                self.get_data();
            }
        });
    },
    
    animate_tweet:function(tweet_html){
        //For more animations
        if(this.$el.attr("view_mode") == "list_mode")
            $(tweet_html).appendTo(this.$el).hide().slideDown("slow");
        else if(this.$el.attr("view_mode") == "box_mode")
            $(tweet_html).appendTo(this.$el).animate({'width': '48.15%'}, 500);
    },
    
});

openerp.website.tweet_wall = openerp.Class.extend({
    template : 'twitter_tweets',
    init : function($el, wall_id, interval_time) {
        this.$el = $el;
        this.get_data_duration = interval_time || 5000;
        this.show_tweet_duation = interval_time || 5000;
        this.wall_id = wall_id;
        this.last_publish_date;
        this.show_tweet = [];
        this.shown_tweet = [];
        this.get_data_interval_id;
        this.show_tweet_interval_id;
    },
    
    start: function(){
        var self = this;
        self.bind_event();
        self.bind_full_screen();
        this.get_data_interval_id =  setInterval(function(){return self.get_data();}, this.get_data_duration);
        this.show_tweet_interval_id = setInterval(function(){self.process_tweet();}, this.show_tweet_duation);
    },
    
    bind_event: function(){
        $('.upload_img').click(function() {
            $("input[type=file]").click();
        });
    },
    
    get_data: function(){
        var self = this;
        if(!this.last_publish_date){
            this.last_publish_date = this.get_current_UTCDate();
        }
        return openerp.jsonRpc("/twitter_wall_tweet_data", 'call', {'wall_id' : self.wall_id, 'published_date' : self.last_publish_date, 'fetch_all' : false}).done(function(data) {
                    if (data.length){
                        self.last_publish_date = data[data.length - 1].published_date;
                        self.show_tweet = self.show_tweet.concat(data);
                    }
                });
    },
    
    get_current_UTCDate: function() {
        var d = new Date();
        return d.getUTCFullYear() +"-"+ (d.getUTCMonth()+1) +"-"+d.getUTCDate()+" "+d.getUTCHours()+":"+d.getUTCMinutes()+":"+d.getUTCSeconds()+"."+d.getUTCMilliseconds();
    },
    
    process_tweet : function() {
        var self = this;
        if (this.show_tweet.length){
            var tweet = self.show_tweet.shift();
            self.shown_tweet.push(tweet);
            str = tweet['tweet'];
            var url_pattern = /(\b(https?):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gi;
            str = str.replace(url_pattern, '<span class="tweet_url_hash_highlight">$1</span>');
            
            var hash_pattern = /(\B#\w*[a-zA-Z]+\w*)/gi;
            str = str.replace(hash_pattern, '<span class="tweet_url_hash_highlight">$1</span>');
            
            var uname_pattern = /(\B@\w*[a-zA-Z]+\w*)/gi;
            str = str.replace(uname_pattern, '<span class="tweet_url_hash_highlight">$1</span>');
            tweet['tweet'] = str;

            if(tweet['back_image'])
                $("div.full_screen").animate({opacity: 0.5}, '1500', function() {
                    $(this).css({'background-image': 'url("data:image/jpg;base64,' + tweet['back_image'] + '")'})
                    .animate({opacity: 1}, '2500');
                });
            this.animate_tweet(openerp.qweb.render("twitter_tweets_"+ self.$el.attr("view_mode"), {'res' : tweet}));
        }
    },

    
    animate_tweet:function(tweet_html){
        //For more animations
        if(this.$el.attr("view_mode") == "list_mode")
            $(tweet_html).prependTo(this.$el).hide().slideDown("slow");
        else if(this.$el.attr("view_mode") == "box_mode")
            $(tweet_html).prependTo(this.$el).animate({'width': '48.15%'}, 100);
    },
    
    bind_full_screen: function(){
        $("header").remove();
        $("footer").remove();
        $("#max_window").on('click',function(){
            $("#website-top-navbar").remove();
            // $(".twitter_wall_container").addClass("twitter_wall_container_top");
            if ((document.fullScreenElement && document.fullScreenElement !== null) || (!document.mozFullScreen && !document.webkitIsFullScreen)) {
               if (document.documentElement.requestFullScreen) {
                    document.documentElement.requestFullScreen();
                } else if (document.documentElement.mozRequestFullScreen) {
                    document.documentElement.mozRequestFullScreen();
                } else if (document.documentElement.webkitRequestFullScreen) {
                    document.documentElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
                }
            } else {
                if (document.cancelFullScreen) {
                    document.cancelFullScreen();
                } else if (document.mozCancelFullScreen) {
                    document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    document.webkitCancelFullScreen();
                }
            }
        });
    }
});