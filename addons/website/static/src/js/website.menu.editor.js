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
            $(".o_parent_menu:not(:has(ul))").children('a').after('<ul class="dropdown-menu o_editable_menu" role="menu"></ul>');
            $(".o_parent_menu").children('a').removeAttr('data-toggle class');
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

	website.snippet.SaveMenu = website.EditorBar.include({
		saveElement: function($el){
			// if($el.hasClass('o_parent_menu')){
   //          	$el.children('ul').css('visibility', '');
   //          	$el.off('mouseenter');
   //          	$el.removeClass('open');
   //          	debugger;
			// 	if($el.find('li').length === 0){
   //          		$el.children('a').children('.caret').remove();
   //          		$el.children('.dropdown-menu').remove();
			// 	}else{
			// 		$el.children('a').attr('data-toggle', 'dropdown');
   //          		$el.children('a').addClass('dropdown-toggle');
			// 	}
			// }
			// debugger;

			var result = this._super($el);

			return result;
		}
	});





})();