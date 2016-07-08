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

"""Default configuration of deposit module."""

from invenio_records_rest.facets import terms_filter
from invenio_records_rest.utils import check_elasticsearch

from .utils import check_oauth2_scope_write, \
    check_oauth2_scope_write_elasticsearch

DEPOSIT_SEARCH_API = '/api/deposits'
"""URL of search endpoint for deposits."""

DEPOSIT_RECORDS_API = '/api/deposits/{pid_value}'
"""URL of record endpoint for deposits."""

DEPOSIT_PID_MINTER = 'recid'
"""PID minter used for record submissions."""

DEPOSIT_JSONSCHEMAS_PREFIX = 'deposits/'
"""Prefix for all deposit JSON schemas."""

DEPOSIT_DEFAULT_JSONSCHEMA = 'deposits/deposit-v1.0.0.json'
"""Default JSON schema used for new deposits."""

DEPOSIT_DEFAULT_SCHEMAFORM = 'json/invenio_deposit/form.json'
"""Default Angular Schema Form."""

_PID = 'pid(depid,record_class="invenio_deposit.api:Deposit")'

DEPOSIT_REST_ENDPOINTS = dict(
    depid=dict(
        pid_type='depid',
        pid_minter='deposit',
        pid_fetcher='deposit',
        record_class='invenio_deposit.api:Deposit',
        files_serializers={
            'application/json': ('invenio_deposit.serializers'
                                 ':json_v1_files_response'),
        },
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_class='invenio_deposit.search:DepositSearch',
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/deposits/',
        item_route='/deposits/<{0}:pid_value>'.format(_PID),
        file_list_route='/deposits/<{0}:pid_value>/files'.format(_PID),
        file_item_route='/deposits/<{0}:pid_value>/files/<path:key>'.format(
            _PID),
        default_media_type='application/json',
        links_factory_imp='invenio_deposit.links:deposit_links_factory',
        create_permission_factory_imp=check_oauth2_scope_write,
        read_permission_factory_imp=check_elasticsearch,
        update_permission_factory_imp=check_oauth2_scope_write_elasticsearch,
        delete_permission_factory_imp=check_oauth2_scope_write_elasticsearch,
        max_result_window=10000,
    ),
)

DEPOSIT_FORM_TEMPLATES = dict(
    default='/static/node_modules/invenio-records-js/dist/'
            'templates/default.html',
    fieldset='/static/node_modules/invenio-records-js/dist/'
             'templates/fieldset.html',
    array='/static/node_modules/invenio-records-js/dist/templates/array.html',
    radios_inline='/static/node_modules/invenio-records-js/dist/'
                  'templates/radios_inline.html',
    radios='/static/node_modules/invenio-records-js/dist/'
           'templates/radios.html',
    select='/static/node_modules/invenio-records-js/dist/'
           'templates/select.html',
    button='/static/node_modules/invenio-records-js/dist/'
           'templates/button.html',
    textarea='/static/node_modules/invenio-records-js/dist/'
             'templates/textarea.html'
)

DEPOSIT_RESPONSE_MESSAGES = dict()
"""Alerts shown when actions are completed on deposit."""

DEPOSIT_REST_SORT_OPTIONS = dict(
    deposits=dict(
        bestmatch=dict(
            fields=['-_score'],
            title='Best match',
            default_order='asc',
            order=2
        ),
        mostrecent=dict(
            fields=['-_updated'],
            title='Most recent',
            default_order='asc',
            order=1
        )
    )
)

DEPOSIT_REST_DEFAULT_SORT = dict(
    deposits=dict(
        query='bestmatch',
        noquery='mostrecent'
    )
)

DEPOSIT_REST_FACETS = dict(
    deposits=dict(
        aggs=dict(
            status=dict(
                terms=dict(field='_deposit.status'),
            )
        ),
        post_filters=dict(
            status=terms_filter('_deposit.status'),
        )
    )
)

DEPOSIT_RECORDS_UI_ENDPOINTS = dict(
    depid=dict(
        pid_type='depid',
        route='/deposit/<pid_value>',
        template='invenio_deposit/edit.html',
        record_class='invenio_deposit.api:Deposit',
    ),
)

DEPOSIT_UI_INDEX_TEMPLATE = 'invenio_deposit/index.html'
"""Index template."""

DEPOSIT_UI_NEW_TEMPLATE = 'invenio_deposit/edit.html'
"""New deposit template."""

DEPOSIT_UI_JSTEMPLATE_ACTIONS = \
    'node_modules/invenio-records-js/dist/templates/actions.html'
DEPOSIT_UI_JSTEMPLATE_ERROR = \
    'node_modules/invenio-records-js/dist/templates/error.html'
DEPOSIT_UI_JSTEMPLATE_FORM = \
    'node_modules/invenio-records-js/dist/templates/form.html'
DEPOSIT_UI_SEARCH_INDEX = 'deposits'
"""Search index name for the deposit."""

DEPOSIT_DEFAULT_STORAGE_CLASS = 'S'
"""Default storage class."""

DEPOSIT_REGISTER_SIGNALS = True
"""Enable the signals registration."""
