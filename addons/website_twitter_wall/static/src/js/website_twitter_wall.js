$(document).ready(function() {
    if(window.location.href.split("/")[3]=="twitter_wall"){
        $('#oe_main_menu_navbar').css("display","none");
        $('header').css("display","none");
        $('footer').css("display",'none');   
    }    
    if($("div[name='tweets_for_client']").length){
        var twitter_wall = new openerp.website.tweet_wall($("#tweet_wall_div"), parseInt($("[wall_id]").attr("wall_id")));
        twitter_wall.start();
    }
});

openerp.website.tweet_wall = openerp.Class.extend({
    template : 'twitter_tweets',
    init : function($el, wall_id, interval_time) {
        this.$el = $el;
        this.twitter_widget = 0;
        this.get_data_duration = interval_time || 5500;
        this.show_tweet_duation = interval_time || 5000;
        this.wall_id = wall_id;
        this.show_tweet = [];
        this.shown_tweet = [];
        this.get_data_interval_id;
        this.show_tweet_interval_id;
        this.last_tweet_id = 0;
    },
    
    start: function(){
        var self = this;
        this.get_data_interval_id =  setInterval(function(){return self.get_data();}, this.get_data_duration);
        this.show_tweet_interval_id = setInterval(function(){self.process_tweet();}, this.show_tweet_duation);
    },
    
    get_data: function(){
        var self = this;
        return openerp.jsonRpc("/twitter_wall/pull_tweet/"+ self.wall_id, 'call', {'last_tweet' : self.last_tweet_id}).done(function(data) {
            if (data){
                self.last_tweet_id = data.id;
                self.show_tweet = self.show_tweet.concat(data);
            }
        });
    },
    
    process_tweet : function() {
        var self = this;

        if (this.show_tweet.length){
            var tweet = self.show_tweet.shift();
            self.shown_tweet.push(tweet);
            this.animate_tweet(openerp.qweb.render("twitter_tweets", {'res' : tweet}));
        }
    },

    animate_tweet:function(tweet_html){
        //$(tweet_html).prependTo(this.$el).hide().slideDown("slow");
        $(tweet_html).prependTo(this.$el);
        setTimeout(function(){
            $('.live-tweet').slideDown("slow");
        },1600);
    }
});