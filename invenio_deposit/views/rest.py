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

import json
from uuid import UUID
from flask import Blueprint, url_for, request, abort, current_app, \
    make_response
from invenio_db import db
from invenio_pidstore.resolver import Resolver
from invenio_records_rest.views import create_url_rules, pass_record
from invenio_rest import ContentNegotiatedMethodView
from sqlalchemy.orm.exc import NoResultFound

from ..serializers import json_files_serializer, json_file_serializer
from ..api import Deposit


def create_blueprint(endpoints):
    """Create Invenio-Deposit-REST blueprint."""
    blueprint = Blueprint(
        'invenio_deposit_rest',
        __name__,
        url_prefix='',
    )

    for endpoint, options in (endpoints or {}).items():
        for rule in create_url_rules(endpoint, **options):
            blueprint.add_url_rule(**rule)

        deposit_actions = DepositActionResource.as_view(
            DepositActionResource.view_name.format(endpoint),
            serializers=options.get('record_serializers'),
            pid_type=options['pid_type'],
        )

        blueprint.add_url_rule(
            '{0}/actions/<any(publish,edit,discard):action>'.format(
                options['item_route']
            ),
            view_func=deposit_actions,
            methods=['POST']
        )

        deposit_files = DepositFilesResource.as_view(
            DepositFilesResource.view_name.format(endpoint),
            serializers=options.get('record_serializers'),
            pid_type=options['pid_type'],
        )

        blueprint.add_url_rule(
            '{0}/files'.format(
                options['item_route']
            ),
            view_func=deposit_files,
            methods=['GET', 'POST']
        )

        deposit_file = DepositFileResource.as_view(
            DepositFileResource.view_name.format(endpoint),
            serializers=options.get('record_serializers'),
            pid_type=options['pid_type'],
        )

        blueprint.add_url_rule(
            '{0}/files/<path:key>'.format(
                options['item_route']
            ),
            view_func=deposit_file,
            methods=['GET', 'PUT', 'DELETE']
        )

    return blueprint


class DepositActionResource(ContentNegotiatedMethodView):
    """"Deposit action resource."""

    view_name = '{0}_actions'

    def __init__(self, serializers, pid_type, *args, **kwargs):
        """Constructor."""
        super(DepositActionResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        self.resolver = Resolver(
            pid_type=pid_type, object_type='rec',
            getter=partial(Deposit.get_record, with_deleted=True)
        )

    @pass_record
    def post(self, pid, record, action):
        """Handle deposit action."""
        getattr(record, action)(pid=pid)
        db.session.commit()

        response = self.make_response(pid, record, 201)
        endpoint = '.{0}_item'.format(pid.pid_type)
        location = url_for(endpoint, pid_value=pid.pid_value, _external=True)
        response.headers.extend(dict(location=location))
        return response


class DepositFilesResource(ContentNegotiatedMethodView):
    """"Deposit files resource."""

    view_name = '{0}_files'

    def __init__(self, serializers, pid_type, *args, **kwargs):
        """Constructor."""
        super(DepositFilesResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        self.resolver = Resolver(
            pid_type=pid_type, object_type='rec',
            getter=partial(Deposit.get_record, with_deleted=True)
        )

    @pass_record
    def get(self, pid, record):
        """Get deposit/depositions/:id/files."""
        return json_files_serializer(record.get_files())

    @pass_record
    def post(self, pid, record):
        """Handle POST deposit files."""
        # file name
        key = request.form['name']
        # load the file
        uploaded_file = request.files['file']
        # add it to the deposit
        obj = record.add_file(
            key=key, stream=uploaded_file.stream,
            storage_class=current_app.config['DEPOSIT_DEFAULT_STORAGE_CLASS']
        )
        db.session.commit()
        return json_file_serializer(obj, status=201)


class DepositFileResource(ContentNegotiatedMethodView):
    """"Deposit files resource."""

    view_name = '{0}_file'

    def __init__(self, serializers, pid_type, *args, **kwargs):
        """Constructor."""
        super(DepositFileResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        self.resolver = Resolver(
            pid_type=pid_type, object_type='rec',
            getter=partial(Deposit.get_record, with_deleted=True)
        )

    @pass_record
    def get(self, pid, record, key, **kwargs):
        """Get deposit/depositions/:id/files/:key."""
        version_id = UUID(request.headers['version_id']) \
            if 'version_id' in request.headers else None
        try:
            return json_file_serializer(record.get_file(
                key=key, version_id=version_id) or abort(404))
        except NoResultFound:
            abort(404)

    @pass_record
    def put(self, pid, record, key):
        """Handle PUT deposit files."""
        data = json.loads(request.data)
        new_key = data['filename']
        if not new_key:
            abort(400)
        try:
            obj = record.rename_file(old_key=key, new_key=new_key)
        except NoResultFound:
            abort(404)
        db.session.commit()
        return json_file_serializer(obj)

    @pass_record
    def delete(self, pid, record, key):
        """Handle DELETE deposit files."""
        if record.delete_file(key=key):
            db.session.commit()
            # FIXME
            return make_response("", 204)
        else:
            abort(404, 'The specified object does not exist or has already '
                  'been deleted.')
