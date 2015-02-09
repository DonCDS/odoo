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
            $(".o_menu_parent:not(:has(ul))").children('a').append('<span class="caret"></span>');
            $(".o_menu_parent:not(:has(ul))").children('a').after('<ul class="dropdown-menu o_editable_menu" role="menu"></ul>');
            $(".o_menu_parent").children('a').removeAttr('data-toggle class');
            $(".o_menu_parent").addClass('open');
            $(".o_menu_parent").children('ul').css('visibility', 'hidden');
            $(".o_menu_parent").droppable({
                over:function(){self.open_dropdown_hover($(this));}
            });
            $("body").on("mouseenter", ".o_menu_parent", function () {
                self.open_dropdown_hover($(this));
            });
        },
    });

	website.snippet.SaveMenu = website.EditorBar.include({
		saveElement: function($el){
			if($el.hasClass('o_menu_parent')){
                //a mettre dans clean_for_save
            	$el.children('ul').css('visibility', '');
            	$el.off('mouseenter');
            	$el.removeClass('open');
				if($el.find('ul').length === 0){
            		$el.children('a').children('.caret').remove();
            		$el.children('.dropdown-menu').remove();
				}else{
					$el.children('a').attr('data-toggle', 'dropdown');
            		$el.children('a').addClass('dropdown-toggle');
				}
                var markup = $el.prop('outerHTML');
                console.log(markup);
                result = openerp.jsonRpc('/website/save_menu', 'save_menu', {
                    value: markup,
                    xpath: $el.data('oe-xpath') || null,
                    context: website.get_context(),
                });
			}else{
                var result = this._super($el);
            }

			return result;
		}
	});





})();