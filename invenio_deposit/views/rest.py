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

import json
from copy import deepcopy
from functools import partial
from uuid import UUID

from flask import Blueprint, url_for, request, abort, current_app, \
    make_response
from invenio_db import db
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.resolver import Resolver
from invenio_records_rest.utils import obj_or_import_string
from invenio_records_rest.views import \
    create_url_rules as records_rest_url_rules, need_record_permission, \
    pass_record
from invenio_rest import ContentNegotiatedMethodView
from invenio_rest.errors import RESTException
from invenio_rest.views import create_api_errorhandler
from sqlalchemy.orm.exc import NoResultFound
from webargs import fields
from webargs.flaskparser import use_kwargs
from invenio_oauth2server import require_api_auth, require_oauth_scopes

from ..api import Deposit
from ..search import DepositSearch
from ..scopes import write_scope


def create_blueprint(endpoints):
    """Create Invenio-Deposit-REST blueprint."""
    blueprint = Blueprint(
        'invenio_deposit_rest',
        __name__,
        url_prefix='',
    )
    blueprint.errorhandler(PIDInvalidAction)(create_api_errorhandler(
        status=403, message='Invalid action'
    ))

    for endpoint, options in (endpoints or {}).items():
        options = deepcopy(options)

        if 'files_serializers' in options:
            files_serializers = options.get('files_serializers')
            files_serializers = {mime: obj_or_import_string(func)
                                 for mime, func in files_serializers.items()}
            del options['files_serializers']
        else:
            files_serializers = {}

        if 'record_serializers' in options:
            serializers = options.get('record_serializers')
            serializers = {mime: obj_or_import_string(func)
                           for mime, func in serializers.items()}
        else:
            serializers = {}

        for rule in records_rest_url_rules(endpoint, **options):
            blueprint.add_url_rule(**rule)

        search_class = obj_or_import_string(
            options['search_class'], default=DepositSearch
        )

        search_class_kwargs = {}
        if options.get('search_index'):
            search_class_kwargs['index'] = options['search_index']

        if options.get('search_type'):
            search_class_kwargs['doc_type'] = options['search_type']

        ctx = dict(
            read_permission_factory=obj_or_import_string(
                options.get('read_permission_factory_imp')
            ),
            create_permission_factory=obj_or_import_string(
                options.get('create_permission_factory_imp')
            ),
            update_permission_factory=obj_or_import_string(
                options.get('update_permission_factory_imp')
            ),
            delete_permission_factory=obj_or_import_string(
                options.get('delete_permission_factory_imp')
            ),
            search_class=partial(search_class, **search_class_kwargs),
        )

        deposit_actions = DepositActionResource.as_view(
            DepositActionResource.view_name.format(endpoint),
            serializers=serializers,
            pid_type=options['pid_type'],
            ctx=ctx,
        )

        blueprint.add_url_rule(
            '{0}/actions/<any(publish,edit,discard):action>'.format(
                options['item_route']
            ),
            view_func=deposit_actions,
            methods=['POST'],
        )

        deposit_files = DepositFilesResource.as_view(
            DepositFilesResource.view_name.format(endpoint),
            serializers=files_serializers,
            pid_type=options['pid_type'],
            ctx=ctx,
        )

        blueprint.add_url_rule(
            '{0}/files'.format(options['item_route']),
            view_func=deposit_files,
            methods=['GET', 'POST', 'PUT'],
        )

        deposit_file = DepositFileResource.as_view(
            DepositFileResource.view_name.format(endpoint),
            serializers=files_serializers,
            pid_type=options['pid_type'],
            ctx=ctx,
        )

        blueprint.add_url_rule(
            '{0}/files/<path:key>'.format(
                options['item_route']
            ),
            view_func=deposit_file,
            methods=['GET', 'PUT', 'DELETE'],
        )
    return blueprint


class DepositActionResource(ContentNegotiatedMethodView):
    """Deposit action resource."""

    view_name = '{0}_actions'

    def __init__(self, serializers, pid_type, ctx, *args, **kwargs):
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
        for key, value in ctx.items():
            setattr(self, key, value)

    @pass_record
    @need_record_permission('update_permission_factory')
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
    """Deposit files resource."""

    view_name = '{0}_files'

    def __init__(self, serializers, pid_type, ctx, *args, **kwargs):
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
        for key, value in ctx.items():
            setattr(self, key, value)

    @pass_record
    @need_record_permission('read_permission_factory')
    def get(self, pid, record):
        """Get deposit/depositions/:id/files."""
        return self.make_response(record.files)

    @require_api_auth()
    @require_oauth_scopes(write_scope.id)
    @pass_record
    @need_record_permission('update_permission_factory')
    def post(self, pid, record):
        """Handle POST deposit files."""
        # file name
        key = request.form['name']
        # load the file
        uploaded_file = request.files['file']
        # add it to the deposit
        record.files[key] = uploaded_file.stream
        record.commit()
        db.session.commit()
        return self.make_response(obj=record.files[key].obj, status=201)

    @require_api_auth()
    @require_oauth_scopes(write_scope.id)
    @pass_record
    @need_record_permission('update_permission_factory')
    def put(self, pid, record):
        """Handle PUT deposit files."""
        ids = [data['id'] for data in json.loads(request.data.decode('utf-8'))]
        record.files.sort_by(*ids)
        record.commit()
        db.session.commit()
        return self.make_response(record.files)


class DepositFileResource(ContentNegotiatedMethodView):
    """Deposit files resource."""

    view_name = '{0}_file'

    get_args = dict(
        version_id=fields.UUID(
            location='headers',
            load_from='version_id',
        ),
    )
    """GET query arguments."""

    def __init__(self, serializers, pid_type, ctx, *args, **kwargs):
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
        for key, value in ctx.items():
            setattr(self, key, value)

    @use_kwargs(get_args)
    @pass_record
    @need_record_permission('read_permission_factory')
    def get(self, pid, record, key, version_id, **kwargs):
        """Get deposit/depositions/:id/files/:key."""
        try:
            obj = record.files[key].get_version(version_id=version_id)
            return self.make_response(obj=obj or abort(404))
        except KeyError:
            abort(404)

    @require_api_auth()
    @require_oauth_scopes(write_scope.id)
    @pass_record
    @need_record_permission('update_permission_factory')
    def put(self, pid, record, key):
        """Handle PUT deposit files."""
        data = json.loads(request.data.decode('utf-8'))
        new_key = data['filename']
        if not new_key:
            abort(400)
        if key in record.files:
            obj = record.files.rename(key, new_key)
            record.commit()
        else:
            abort(404)
        db.session.commit()
        return self.make_response(obj=obj)

    @require_api_auth()
    @require_oauth_scopes(write_scope.id)
    @pass_record
    @need_record_permission('update_permission_factory')
    def delete(self, pid, record, key):
        """Handle DELETE deposit files."""
        try:
            del record.files[key]
            record.commit()
            db.session.commit()
            return make_response('', 204)
        except KeyError:
            abort(404, 'The specified object does not exist or has already '
                  'been deleted.')
