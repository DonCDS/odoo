odoo.define('mail.utils', ['web.session'], function (require) {

    var session = require('web.session');
    /**
     * ------------------------------------------------------------
     * ChatterUtils
     * ------------------------------------------------------------
     * 
     * This class holds a few tools method for Chatter.
     * Some regular expressions not used anymore, kept because I want to
     * - (^|\s)@((\w|@|\.)*): @login@log.log
     * - (^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]: [ir.attachment,3|My Label],
     *   for internal links
     */

     var exports = {};

    /** parse text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False */
    exports.parse_email = function (text) {
        var result = text.match(/(.*)<(.*@.*)>/);
        if (result) {
            return [_.str.trim(result[1]), _.str.trim(result[2])];
        }
        result = text.match(/(.*@.*)/);
        if (result) {
            return [_.str.trim(result[1]), _.str.trim(result[1])];
        }
        return [text, false];
    };

    /* Get an image in /web/binary/image?... */
    exports.get_image = function (session, model, field, id, resize) {
        var r = resize ? encodeURIComponent(resize) : '';
        id = id || '';
        return session.url('/web/binary/image', {model: model, field: field, id: id, resize: r});
    };

    /* Get the url of an attachment {'id': id} */
    exports.get_attachment_url = function (session, message_id, attachment_id) {
        return session.url('/mail/download_attachment', {
            'model': 'mail.message',
            'id': message_id,
            'method': 'download_attachment',
            'attachment_id': attachment_id
        });
    };

    /**
     * Replaces some expressions
     * - :name - shortcut to an image
     */
    exports.do_replace_expressions = function (string) {
        var icon_list = ['al', 'pinky']
        /* special shortcut: :name, try to find an icon if in list */
        var regex_login = new RegExp(/(^|\s):((\w)*)/g);
        var regex_res = regex_login.exec(string);
        while (regex_res != null) {
            var icon_name = regex_res[2];
            if (_.include(icon_list, icon_name))
                string = string.replace(regex_res[0], regex_res[1] + '<img src="/mail/static/src/img/_' + icon_name + '.png" width="22px" height="22px" alt="' + icon_name + '"/>');
            regex_res = regex_login.exec(string);
        }
        return string;
    };

    /**
     * Replaces textarea text into html text (add <p>, <a>)
     * TDE note : should be done server-side, in Python -> use mail.compose.message ?
     */
    exports.get_text2html = function (text) {
        return text
            .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
            .replace(/[\n\r]/g,'<br/>')                
    };

    /* Returns the complete domain with "&" 
     * TDE note: please add some comments to explain how/why
     */
    exports.expand_domain = function (domain) {
        var new_domain = [];
        var nb_and = -1;
        // TDE note: smarted code maybe ?
        for ( var k = domain.length-1; k >= 0 ; k-- ) {
            if ( typeof domain[k] != 'array' && typeof domain[k] != 'object' ) {
                nb_and -= 2;
                continue;
            }
            nb_and += 1;
        }

        for (var k = 0; k < nb_and ; k++) {
            domain.unshift('&');
        }

        return domain;
    };

    // inserts zero width space between each letter of a string so that
    // the word will correctly wrap in html boxes smaller than the text
    exports.breakword = function(str){
        var out = '';
        if (!str) {
            return str;
        }
        for(var i = 0, len = str.length; i < len; i++){
            out += _.str.escapeHTML(str[i]) + '&#8203;';
        }
        return out;
    };

    return exports;
});
