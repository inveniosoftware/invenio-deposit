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

from invenio_assets import NpmBundle

js = NpmBundle(
    'node_modules/angular/angular.js',
    'node_modules/angular-sanitize/angular-sanitize.js',
    'node_modules/objectpath/lib/ObjectPath.js',
    'node_modules/tv4/tv4.js',
    'node_modules/angular-schema-form/dist/schema-form.js',
    'node_modules/angular-schema-form/dist/bootstrap-decorator.js',
    'js/invenio_deposit/app.js',
    filters='jsmin',
    output='gen/deposit.%(version)s.js',
    npm={
        'almond': '~0.3.1',
        'angular': '~1.4.9',
        'angular-sanitize': '~1.4.9',
        'angular-schema-form': '~0.8.13',
        'tv4': '~1.2.7',
        'objectpath': '~1.2.1',
    },
)
