(function() {
    "use strict";
    var website = openerp.website;
    var image = '';
    website.add_template_file('/website_twitter_wall/static/src/xml/website_twitter_wall_creator.xml');
    website.EditorBarContent.include({
        new_twitter_wall: function() {
            (new website.create_twitter_wall(this)).appendTo($(document.body));
        },
    });
    website.create_twitter_wall = openerp.Widget.extend({
        template: 'create_twitter_wall',
        events: {
            'click a': 'create',
            'change .image_upload': 'image_upload',
            'change .image_url': 'image_url',
            'click .list-group-item': function(e) {
                this.$el.find('.list-group-item').removeClass('active');
                this.$el.find(e.target).closest('li').addClass('active');
            }
        },
        start: function() {
            this.$el.modal(); // Open Modal
        },
        image_upload: function(e) {
            var self = this;
            this.error("");
            this.$el.find("div.error-dialog").remove();
            image = '';
            this.$el.find('input.image_url').val("");
            this.$el.find('.image').attr('src','/website_twitter_wall/static/src/img/document.png');
            var fileName = e.target.files[0];
            var fr = new FileReader();
            fr.onload = function(ev) {
                self.$el.find('.image').attr('src', ev.target.result);
                image = ev.target.result.split(',')[1]
            }
            fr.readAsDataURL(fileName);
        },
        image_url: function(e) {
            image = '';
            var testRegex = /^https?:\/\/(?:[a-z\-]+\.)+[a-z]{2,6}(?:\/[^\/#?]+)+\.(?:jpe?g|gif|png)$/;
            this.$el.find(".image_upload").val("");
            this.$el.find('.image').attr('src','/website_twitter_wall/static/src/img/document.png');
            this.error("");
            this.$el.find("div.error-dialog").remove();
            var url = e.target.value;
            if (testRegex.test(url)) {
                this.$el.find('.image').attr('src', url);
                image = url;
            } else {
                this.$el.find('.url-error').removeClass("hidden");
                this.$el.find('.image_url').focus();
                e.target.value = "";
                return;
            }
        },
        create: function(e) {
            var self = this;
            var modal = this.$el.find(".modal-content");
            var wall_name = modal.find(".text-wallname").val().trim();
            var wall_description = modal.find(".text-description").val().trim();
            if(!image) {
                this.error("Upload Image");
                return;
            }
            if(wall_name == '') {
                this.error("Must Enter Wall Name");
                return;
            }
            if(wall_description == '') {
                this.error("Enter Description");
                return;
            }
            this.$el.find('.modal-footer, .modal-body').hide();
            this.$el.find('.wall-creating').removeClass("hidden");
            $.ajax({
                url: '/create_twitter_wall',
                type: 'post',
                data: {
                    'name': wall_name,
                    'image': image,
                    'description': wall_description,
                    'publish': !self.$el.find(e.target).hasClass("draft"),
                },
                success: function(data) {
                    self.$el.modal('hide');
                    window.location = "/twitter_walls";
                }
            });
        },
        error: function (msg) {
            this.$el.find(".error_msg").html("<div class='error-dialog alert alert-danger alert-dismissible' role='alert'>"+ msg +"</div>");
        },
    });
})();