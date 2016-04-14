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

from flask_login import current_user
from elasticsearch_dsl import Q


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

DEPOSIT_REST_ENDPOINTS = dict(
    dep=dict(
        pid_type='dep',
        pid_minter='deposit',
        pid_fetcher='deposit',
        search_index='deposits',
        search_type=None,
        record_class='invenio_deposit.api:Deposit',
        record_filter=lambda: Q(
            'match', **{'_deposit.owner': current_user.get_id()}
        ),
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/deposits/',
        item_route='/deposits/<pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
    ),
)

DEPOSIT_RECORDS_UI_ENDPOINTS = dict(
    deposit=dict(
        pid_type='dep',
        route='/deposit/<pid_value>',
        template='invenio_deposit/edit.html',
        record_class='invenio_deposit.api:Deposit',
    ),
)
