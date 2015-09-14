/*
 * This file is part of Invenio.
 * Copyright (C) 2015 CERN.
 *
 * Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */

require([
    'jquery',
    'vendors/base-64/base64',
    'vendors/utf8/utf8',
    'select2'
  ],
  function($, base64, utf8, _select2) {
  'use strict';

  $(function() {
    JSONEditor.defaults.options.ajax = true;
    JSONEditor.defaults.options.disable_collapse = true;
    JSONEditor.defaults.options.disable_edit_json = true;
    JSONEditor.defaults.options.disable_properties = true;
    JSONEditor.defaults.options.iconlib = 'fontawesome4';
    JSONEditor.defaults.options.no_additional_properties = true;
    JSONEditor.defaults.options.theme = 'bootstrap3';
    JSONEditor.defaults.options.remove_empty_properties = true;

    // IE<10 does ont support native base64 methods
    // on the other hand, base64 does not work with almond.js
    // => so, no IE<10 with ASSET_DEBUG=True
    var b64decode = window.atob || base64.decode;
    var b64encode = window.btoa || base64.encode;

    /* JSON blob:
     *   // secure string
     *   base64:
     *     // 0x00-0xFF string (UTF-8)
     *     utf-8:
     *       // browser UTF-16 string, other string, ...
     *       stringify:
     *         JSON object
     */
    function json2blob(json) {
        if ($.isEmptyObject(json)) {
            return '';
        } else {
            return base64.encode(utf8.encode(JSON.stringify(json)));
        }
    }
    function blob2json(blob) {
        var str = utf8.decode(base64.decode(blob)).trim();
        if (str) {
            return JSON.parse(str);
        } else {
            return {};
        }
    }

    $('.jsondeposit').each(function() {
        var element = this;
        $.getJSON($(element).data('schema'), function(schema) {
            var loading = $('.jsondeposit-loading', element)[0];
            var target = $('.jsondeposit-rendered', element)[0];
            var editor = new JSONEditor(target, {
                form_name_root: $(element).data('id'),
                schema: schema,
            });


            var json = $('.jsondeposit-blob', element)[0];
            var initial_state = blob2json($(json).text());
            editor.on('ready', function() {
                if (!$.isEmptyObject(initial_state)) {
                    editor.setValue(initial_state);
                }
                editor.on('change', function() {
                    $(json).text(json2blob(editor.getValue()));
                });

                $(loading).remove();
            });
        });
    });
  });
})
