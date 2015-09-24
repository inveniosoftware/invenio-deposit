# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Deposit bundles."""

from __future__ import unicode_literals

from invenio_base.bundles import invenio as _i
from invenio_base.bundles import jquery as _j

from invenio_ext.assets import Bundle, RequireJSFilter
from invenio_ext.assets.filter import CSSUrlFixer

js = Bundle(
    "vendors/plupload/js/moxie.js",
    "vendors/plupload/js/plupload.dev.js",
    "vendors/json-editor/dist/jsoneditor.js",
    "js/deposit/init.js",
    "js/deposit/jsonwidget.js",
    output="deposit.js",
    filters=RequireJSFilter(exclude=[_j, _i]),
    weight=51,
    bower={
        "plupload": "latest",
        "ckeditor": "latest",
        "flight": "latest",
        "eonasdan-bootstrap-datetimepicker": "4.14.30",
        "base-64": "latest",
        "json-editor": "latest",
        "select2": "~3",
        "utf8": "latest",
    }
)

styles = Bundle(
    "css/deposit/form.css",
    "vendors/eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.css",  # noqa
    Bundle(
        "less/deposit/jsonwidget.less",
        Bundle(
            "vendors/select2/select2.css",
            "vendors/select2/select2-bootstrap.css",
            filters=CSSUrlFixer('vendors/select2'),
            output="select2_fixed.css"
        ),
        output='jsondeposit.css',
        filters="less,cleancss",
    ),
    output="deposit.css",
    filters="cleancss",
    weight=51
)
