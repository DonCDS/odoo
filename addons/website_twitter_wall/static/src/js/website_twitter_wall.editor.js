(function() {
    "use strict";
    var website = openerp.website;
    var wall_name = '';
    var wall_description = '';
    var image = '';
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
            $modal.modal();
        },
        image_upload: function(e){
            var self = this;
            self.error("");
            image = '';
            this.$("div.error-dialog").remove();
            this.$('input[name="url"]').val("");
            this.$('#image').attr('src','/website_twitter_wall/static/src/img/document.png');
            var fileName = e.target.files[0];
            var fr = new FileReader();
            fr.onload = function(ev){
                $('.show_image img').remove();
                $('.show_image').html("<span class='oe-image-thumbnail slide-img-border' style='max-height: 168px;'><img src='"+ev.target.result+"' id='image' class='img-responsive' title='Preview' style='width: 100%;'/></span>");
                image = ev.target.result.split(',')[1]
                console.log(image);
            }
            fr.readAsDataURL(fileName);
        },
        image_url:function(e){
            var self = this;
            image = '';
            this.$('.url-error').hide();
            var testRegex = /^https?:\/\/(?:[a-z\-]+\.)+[a-z]{2,6}(?:\/[^\/#?]+)+\.(?:jpe?g|gif|png)$/;
            this.$("#image_upload").val("");
            this.$('#image').attr('src','/website_twitter_wall/static/src/img/document.png');
            self.error("");
            this.$("div.error-dialog").remove();
            var url = e.target.value;
            if (testRegex.test(url)){
                this.$('.show_image img').remove();
                this.$('.show_image').html("<span class='oe-image-thumbnail slide-img-border' style='max-height: 168px;'><img src='"+url+"' id='image' class='img-responsive' title='Preview' style='width: 100%;'/></span>");
                image = url;
            }else{
                this.$('.url-error').show();
                this.$('#image_url').focus();
                e.target.value = "";
                return;
            }            
        },
        text_wallname:function(e){
            var self = this;
            wall_name = '';
            if (e.target.value.length > 0){
                self.error("");
                wall_name = e.target.value;
                this.$("div.error-dialog").remove();    
            }else{
                self.error("Must Enter Wall Name");
                return false;
            }
            
        },
        text_description:function(e){
            var self = this;
            wall_description = '';
            if (e.target.value.length > 0){
                self.error("");
                wall_description = e.target.value;
                this.$("div.error-dialog").remove();    
            }else{
                self.error("Enter description");
                return false;
            }
        },
        save: function () {
            console.log("SAve" + wall_name);
            var self = this;
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