(function () {
    'use strict';
    var website = openerp.website;

    website.snippet.MenuEditor = website.snippet.BuildingBlock.include({

    	start: function() {
    		this._super();
    		this.init_edit_menu();
    	},

    	open_dropdown_hover: function(snippet){
            if(!snippet.hasClass('oe_current_dropdown')){
                $('.oe_current_dropdown').children('ul').css('visibility', 'hidden');
                $('.oe_current_dropdown').removeClass("oe_current_dropdown");
                snippet.addClass("oe_current_dropdown");
                snippet.children('ul').css('visibility', 'visible');
                this.make_active(false);
            }
        },

        init_edit_menu: function(){
            var self = this;
            $("#wrapwrap").click(function(event){
                if(!$(event.target).hasClass('.dropdown-menu') &&
                    $(event.target).parents('.dropdown-menu').length === 0){
                    $('.oe_current_dropdown').children('ul').css('visibility', 'hidden');
                    $('.oe_current_dropdown').removeClass("oe_current_dropdown");
                }
            });
            $(".o_parent_menu:not(:has(ul))").children('a').append('<span class="caret"></span>');
            $(".o_parent_menu:not(:has(ul))").children('a').after('<ul class="dropdown-menu o_editable_menu" role="menu"><li class="o_editable"></li></ul>');
            $(".o_parent_menu").children('a').removeAttr('data-toggle href class');
            $(".o_parent_menu").addClass('open');
            $(".o_parent_menu").children('ul').css('visibility', 'hidden');
            $(".o_parent_menu").droppable({
                over:function(){self.open_dropdown_hover($(this));}
            });
            $("body").on("mouseenter", ".o_parent_menu", function () {
                self.open_dropdown_hover($(this));
            });
        },
    });





})();