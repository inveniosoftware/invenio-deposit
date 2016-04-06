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

"""Deposit actions."""

from __future__ import absolute_import, print_function

from functools import partial

from flask import Blueprint, abort, current_app, request, url_for
from flask_login import current_user
from invenio_db import db
from invenio_pidstore.resolver import Resolver
from invenio_records_rest.views import pass_record
from invenio_rest import ContentNegotiatedMethodView
from sqlalchemy.exc import SQLAlchemyError

from ..api import Deposit
from ..serializers import json_serializer

blueprint = Blueprint(
    'invenio_deposit_rest_actions',
    __name__,
    url_prefix='/deposits'
)


class DepositActionResource(ContentNegotiatedMethodView):
    """"Deposit action resource."""

    def __init__(self, serializers=None, *args, **kwargs):
        """Constructor."""
        super(DepositActionResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        self.resolver = Resolver(
            pid_type='deposit', object_type='rec',
            getter=partial(Deposit.get_record, with_deleted=True)
        )

    @pass_record
    def post(self, pid, record, action):
        """Handle deposit action."""
        getattr(record, action)(pid=pid)
        db.session.commit()

        response = self.make_response(pid, record, 201)
        endpoint = 'invenio_records_rest.{0}_item'.format(pid.pid_type)
        location = url_for(endpoint, pid_value=pid.pid_value, _external=True)
        response.headers.extend(dict(location=location))
        return response


# FIXME use same serializer as record REST API.
serializers = {
    'application/json': json_serializer,
}

deposit_actions = DepositActionResource.as_view(
    'deposit_action_api',
    serializers=serializers
)

blueprint.add_url_rule(
    '/<string:pid_value>/actions/<any(publish,edit,discard):action>',
    view_func=deposit_actions,
    methods=['POST']
)
