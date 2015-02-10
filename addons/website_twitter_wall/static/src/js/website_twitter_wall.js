$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip();
    $("timeago.timeago").timeago();
    if($("div[name='tweets_for_client']").length) {
        var twitter_wall = new openerp.website.tweet_wall($("#tweet_wall_div"), parseInt($("#tweet_wall_div").attr("wall_id")));
        twitter_wall.start();
    }
});

openerp.qweb.add_template('/website_twitter_wall/static/src/xml/website_twitter_wall.xml');
openerp.website.tweet_wall = openerp.Class.extend({
    template: 'twitter_tweets',
    init: function($el, wall_id, interval_time) {
        this.$el = $el;
        this.interval_time = interval_time || 2000;
        this.wall_id = wall_id;
        this.show_tweet = [];
        this.last_tweet_id = 0;
    },

    // Hide header and footer, Start to get and display tweet based on interval time
    start: function() {
        var self = this;
        $('#oe_main_menu_navbar, header, footer, .options').css("display", "none");
        $(".navbar").on("mouseover", function(){$(".options").show();});
        $(".navbar").on("mouseleave", function(){$(".options").hide();});
        setInterval(function() { return self.get_data(); }, this.interval_time);
        setInterval(function() { self.process_tweet(); }, this.interval_time);
    },

    // Get tweet
    get_data: function() {
        var self = this;
        return openerp.jsonRpc("/twitter_wall/pull_tweet/" + this.wall_id, 'call', {'last_tweet': this.last_tweet_id}).done(function(data) {
            if (data){
                self.last_tweet_id = data.id;
                self.show_tweet = self.show_tweet.concat(data);
            }
        });
    },

    // Display tweet
    process_tweet: function() {
        if (this.show_tweet.length)
            $(openerp.qweb.render("twitter_tweets", {'res': this.show_tweet.shift()})).prependTo(this.$el);
    },
});