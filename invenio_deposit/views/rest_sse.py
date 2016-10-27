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

"""Deposit SSE."""

from __future__ import absolute_import, print_function

from copy import deepcopy

from flask import Blueprint, Response, url_for
from flask.views import MethodView
from invenio_records_rest.utils import obj_or_import_string
from invenio_records_rest.views import need_record_permission, pass_record

from invenio_deposit.search import DepositSearch


def create_blueprint(endpoints, url_prefix=''):
    """Create Invenio-Deposit-REST blueprint.

    See: :data:`invenio_deposit.config.DEPOSIT_REST_ENDPOINTS`.

    :param endpoints: List of endpoints configuration.
    :param url_prefix: Prefix of the blueprint's URL.
    :returns: The configured blueprint.
    """
    blueprint = Blueprint(
        'invenio_deposit_sse',
        __name__,
        url_prefix=url_prefix,
    )

    for endpoint, options in (endpoints or {}).items():
        options = deepcopy(options)

        ctx = dict(
            read_permission_factory=obj_or_import_string(
                options.get('read_permission_factory_imp')
            ),
            search_class=obj_or_import_string(
                options.get('search_class', DepositSearch)
            ),
        )

        # Extend blueprint for SSE
        deposit_sse = DepositSSE.as_view(
            DepositSSE.view_name.format(endpoint),
            pid_type=options['pid_type'],
            ctx=ctx
        )

        # Add URL rule to given blueprint
        blueprint.add_url_rule(
            '{0}/sse'.format(options['item_route']),
            view_func=deposit_sse,
            methods=['GET'],
        )

    return blueprint


class DepositSSE(MethodView):
    """Deposit SSE channel resource."""

    view_name = '{0}_sse'

    def __init__(self, pid_type, ctx):
        """Constructor."""
        for key, value in ctx.items():
            setattr(self, key, value)

    @pass_record
    @need_record_permission('read_permission_factory')
    def get(self, pid, record):
        """Initiate SSE connection.

        Permission required: `read_permission_factory`.

        :param pid: Pid object (from url).
        :param record: Record object resolved from the pid.
        :returns: the established SSE channel.
        """
        from invenio_sse import current_sse
        channel = url_for('.depid_sse', pid_value=pid.pid_value)
        return Response(
            current_sse.messages(channel=channel),
            mimetype='text/event-stream',
        )
