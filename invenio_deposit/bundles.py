# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""UI for Invenio-Deposit."""

from flask_assets import Bundle
from invenio_assets import NpmBundle

css = Bundle(
    'node_modules/ui-select/dist/select.css',
    filters='cleancss',
    output='gen/deposit.%(version)s.css',
)

js = NpmBundle(
    'node_modules/angular/angular.js',
    'node_modules/angular-sanitize/angular-sanitize.js',
    'node_modules/angular-animate/angular-animate.js',
    'node_modules/angular-strap/dist/angular-strap.js',
    'node_modules/angular-strap/dist/angular-strap.tpl.js',
    'node_modules/underscore/underscore-min.js',
    'node_modules/angular-underscore/index.js',
    'node_modules/ui-select/dist/select.js',
    'node_modules/angular-translate/dist/angular-translate.js',
    'node_modules/objectpath/lib/ObjectPath.js',
    'node_modules/tv4/tv4.js',
    'node_modules/angular-schema-form/dist/schema-form.js',
    'node_modules/angular-schema-form/dist/bootstrap-decorator.js',
    'node_modules/angular-schema-form-dynamic-select/'
    'angular-schema-form-dynamic-select.js',
    'node_modules/invenio-records-js/dist/invenio-records-js.js',
    'js/invenio_deposit/app.js',
    filters='jsmin',
    output='gen/deposit.%(version)s.js',
    npm={
        'almond': '~0.3.1',
        'angular': '~1.4.9',
        'underscore': '~1.8.3',
        'angular-sanitize': '~1.4.9',
        'angular-animate': '~1.4.8',
        'angular-strap': '~2.3.9',
        'angular-underscore': '~0.0.3',
        'angular-ui-select': 'git://github.com/angular-ui/ui-select#v0.18.0',
        'angular-translate': '~2.11.0',
        'angular-schema-form': '~0.8.13',
        'angular-schema-form-dynamic-select': '~0.13.1',
        'invenio-records-js': '~0.0.1',
        'objectpath': '~1.2.1',
        'tv4': '~1.2.7',
    },
)
