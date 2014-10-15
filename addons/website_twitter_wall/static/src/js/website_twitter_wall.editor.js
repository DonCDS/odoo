(function() {
    "use strict";
    var website = openerp.website;
    var wall_name = '';
    var wall_description = '';
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
            'change .text-wallname':'text_wallname',
            'change .text-description':'text_description',
            'click .list-group-item': function (ev) {
                this.$('.list-group-item').removeClass('active');
                $(ev.target).closest('li').addClass('active');
            }
        },
        start: function () {
            var self = this;
            var $modal = self.$el;
            // $("#myTags").tagit();
            $modal.modal();
            $("#h_ele").val("");
            //$('#image').attr('src','/website_twitter_wall/static/src/img/document.png');
        },
        image_upload: function(e){
            var self = this;
            $("#h_ele").val("");
            self.error("");
            $("div.error-dialog").remove();
            $('input[name="url"]').val("");
            var fileName = e.target.files[0];
            var fr = new FileReader();
            fr.onload = function(ev){
                $('.show_image img').remove();
                $('.show_image').html("<span class='oe-image-thumbnail slide-img-border' style='max-height: 168px;'><img src='"+ev.target.result+"' id='image' class='img-responsive' title='Preview' style='width: 100%;'/></span>");
                //$("#image").removeAttr("src").attr("src",ev.target.result)
                $("#h_ele").val(ev.target.result.split(',')[1]);
            }
            fr.readAsDataURL(fileName);
        },
        image_url:function(e){
            var self = this;
            var testRegex = /^https?:\/\/(?:[a-z\-]+\.)+[a-z]{2,6}(?:\/[^\/#?]+)+\.(?:jpe?g|gif|png)$/;
            $("#h_ele").val("");
            $("#image_upload").val("");
            self.error("");
            $("div.error-dialog").remove();
            var url = e.target.value;
            if (testRegex.test(url)){
                $('.show_image img').remove();
                $('.show_image').html("<span class='oe-image-thumbnail slide-img-border' style='max-height: 168px;'><img src='"+url+"' id='image' class='img-responsive' title='Preview' style='width: 100%;'/></span>");
                $("#h_ele").val(url);                 
            }else{
                self.error("");
                self.error("Enter valid image URL.");
                e.target.value = "";
                return;
            }            
        },
        text_wallname:function(e){
            var self = this;
            if (e.target.value.length > 0){
                self.error("");
                wall_name = e.target.value;
                $("div.error-dialog").remove();    
            }else{
                return false;
            }
            
        },
        text_description:function(e){
            var self = this;
            if (e.target.value.length > 0){
                self.error("");
                wall_description = e.target.value;
                $("div.error-dialog").remove();    
            }else{
                return false;
            }
        },
        save: function () {
            console.log("SAve" + wall_name);
            var self = this;
            var image = $("#h_ele").val();
            var include_retweet = ($('#include_retweet').attr('checked'))?'TRUE':'FALSE';
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
            this.$('.modal-footer').hide();
            this.$('.modal-body').hide()
            this.$('.wall-creating').show();
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
            $(".error_msg").html("<div class='error-dialog alert alert-danger alert-dismissible' role='alert'>"+ msg +"</div>");
        },
    });
})();