(function() {
    "use strict";
    var website = openerp.website;
    website.add_template_file('/website_twitter_wall/static/src/xml/website_twitter_wall_editor.xml');
    website.EditorBarContent.include({
        new_twitter_wall: function () {
            (new website.create_twitter_wall(this)).appendTo($(document.body));
        },
    });
    
    
    website.create_twitter_wall = openerp.Widget.extend({
        template: 'create_twitter_wall',
        events: {
            'click #save': 'save',
        },
        start: function () {
            var self = this;
            var $modal = self.$el;
            // $("#myTags").tagit();
            $modal.modal();
        },
        save: function () {
            var self = this;
            var wall_name = $('#wall_name').val();
            var include_retweet = ($('#include_retweet').attr('checked'))?'TRUE':'FALSE';
            var wall_description = $('#wall_description').val();
            if(wall_name.trim() == ''){
                self.error("Must Enter Wall Name");
                return;
            }
            $.ajax({
                url: '/create_twitter_wall',
                type: 'post',
                data:{
                    'wall_name':wall_name,
                    'include_retweet':include_retweet,
                    'wall_description':wall_description
                },
                success: function(data) {
                    self.$el.modal('hide');
                    window.location="/twitter_walls";
                }
            });
        },
        error: function (msg) {
            $(".error_msg").html("<div class='alert alert-danger alert-dismissible' role='alert'>"+ msg +"</div>");
        },
    });
})();