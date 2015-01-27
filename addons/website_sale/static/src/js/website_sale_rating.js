(function () {
    'use strict';

    openerp.website_sale = openerp.website_sale || {};
    var website = openerp.website;
    var instance = openerp.website_sale;

    instance.rating_card = false;
    instance.ProductRating = openerp.Widget.extend({
        events: {
            "mousemove .stars" : "moveOnStars",
            "mouseleave .stars" : "moveOut",
            "click .stars" : "clickOnStar",
        },
        _setup: function(){
            this.star_list = this.$('.stars').find('i');
            this.set("star_index", -1);
            this.on("change:star_index", this, this.changeStars);
        },
        setElement: function($el){
            this._super.apply(this, arguments);
            this._setup();
        },
        changeStars: function(){
            var index = this.get("star_index") + 1;
            this.star_list.removeClass('fa-star').addClass('fa-star-o');
            this.$('.stars').find("i:lt("+index+")").removeClass('fa-star-o').addClass('fa-star');
        },
        moveOut: function(){
            this.set("star_index", -1);
        },
        moveOnStars: function(e){
            var index = this.star_list.index(e.target);
            this.set("star_index", index);
        },
        clickOnStar: function(ev){
            console.log('click', this.get("star_index")+1);
        },
    });


    website.ready().then(function(){
        instance.rating_card = new instance.ProductRating().setElement($('.rating-card'));
    });

}());
