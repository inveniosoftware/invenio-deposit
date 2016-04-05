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

from invenio_records_rest.config import RECORDS_REST_ENDPOINTS

DEPOSIT_SEARCH_API = '/api/deposits'
"""URL of search endpoint for deposits."""

DEPOSIT_RECORDS_REST_ENDPOINTS = dict(
    deposit=dict(
        pid_type='deposit',
        pid_minter='deposit',
        pid_fetcher='deposit',
        search_index='deposits',
        search_type=None,
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
        pid_type='deposits',
        route='/deposits/<pid_value>',
        template='invenio_records_ui/detail.html',
    ),
)

DEPOSIT_RECORDS_REST_ENDPOINTS.update(RECORDS_REST_ENDPOINTS)
