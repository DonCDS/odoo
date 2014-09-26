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
            'change #image_upload':'image_upload',
            'change #image_url':'image_url',
        },
        start: function () {
            var self = this;
            var $modal = self.$el;
            // $("#myTags").tagit();
            $modal.modal();
        },
        image_upload: function(e){
            $("#image_url").val("");
            var fileName = e.target.files[0];
            var fr = new FileReader();
            fr.onload = function(ev){
                $("#image").attr('src',ev.target.result);
                $("#h_ele").val(ev.target.result.split(',')[1]);
            }
            fr.readAsDataURL(fileName);
        },
        image_url:function(e){
            $("#image_upload").val("");
            var url = $('#image_url').val();
            $("#image").attr('src',url);
            $("#h_ele").val(url.split(',')[1]);
        },
        save: function () {
            var self = this;
            var image = $("#h_ele").val();
            var wall_name = $('#wall_name').val();
            var include_retweet = ($('#include_retweet').attr('checked'))?'TRUE':'FALSE';
            var wall_description = $('#wall_description').val();
            if(!image){
                self.error("");
                self.error("Upload Image.");
                return;
            }
            if(wall_name.trim() == ''){
                self.error("");
                self.error("Must Enter Wall Name");
                return;
            }
            if(wall_description.trim() == ''){
                self.error("");
                self.error("Enter description");
                return;
            }
            $.ajax({
                url: '/create_twitter_wall',
                type: 'post',
                data:{
                    'wall_name':wall_name,
                    'image':image,
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