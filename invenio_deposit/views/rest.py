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

from flask import Blueprint, abort, current_app, make_response, request, \
    url_for
from invenio_db import db
from invenio_files_rest.errors import InvalidOperationError
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_pidstore.errors import PIDInvalidAction
from invenio_records_rest.utils import obj_or_import_string
from invenio_records_rest.views import \
    create_url_rules as records_rest_url_rules
from invenio_records_rest.views import need_record_permission, pass_record
from invenio_rest import ContentNegotiatedMethodView
from invenio_rest.views import create_api_errorhandler
from jsonschema.exceptions import ValidationError
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.utils import secure_filename

from ..api import Deposit
from ..errors import FileAlreadyExists, WrongFile
from ..scopes import write_scope
from ..search import DepositSearch
from ..signals import post_action


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
    blueprint.errorhandler(InvalidOperationError)(create_api_errorhandler(
        status=403, message='Invalid operation'
    ))
    blueprint.errorhandler(ValidationError)(create_api_errorhandler(
        status=400, message='Validation error'
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

        file_list_route = options.pop(
            'file_list_route',
            '{0}/files'.format(options['item_route'])
        )
        file_item_route = options.pop(
            'file_item_route',
            '{0}/files/<path:key>'.format(options['item_route'])
        )

        options.setdefault('search_class', DepositSearch)
        search_class = obj_or_import_string(options['search_class'])

        # records rest endpoints will use the deposit class as record class
        options.setdefault('record_class', Deposit)
        record_class = obj_or_import_string(options['record_class'])

        for rule in records_rest_url_rules(endpoint, **options):
            blueprint.add_url_rule(**rule)

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
            record_class=record_class,
            search_class=partial(search_class, **search_class_kwargs),
            default_media_type=options.get('default_media_type'),
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
            file_list_route,
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
            file_item_route,
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
            default_media_type=ctx.get('default_media_type'),
            *args,
            **kwargs
        )
        for key, value in ctx.items():
            setattr(self, key, value)

    @pass_record
    @need_record_permission('update_permission_factory')
    def post(self, pid, record, action):
        """Handle deposit action."""
        getattr(record, action)(pid=pid)

        db.session.commit()
        # Refresh the PID and record metadata
        db.session.refresh(pid)
        db.session.refresh(record.model)
        post_action.send(current_app._get_current_object(), action=action,
                         pid=pid, deposit=record)
        response = self.make_response(pid, record,
                                      202 if action == 'publish' else 201)
        endpoint = '.{0}_item'.format(pid.pid_type)
        location = url_for(endpoint, pid_value=pid.pid_value, _external=True)
        response.headers.extend(dict(Location=location))
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
        # load the file
        uploaded_file = request.files['file']
        # file name
        key = secure_filename(
            request.form.get('name') or uploaded_file.filename
        )
        # check if already exists a file with this name
        if key in record.files:
            raise FileAlreadyExists()
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
        try:
            ids = [data['id'] for data in json.loads(
                request.data.decode('utf-8'))]
        except KeyError:
            raise WrongFile()

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
        for key, value in ctx.items():
            setattr(self, key, value)

    @use_kwargs(get_args)
    @pass_record
    @need_record_permission('read_permission_factory')
    def get(self, pid, record, key, version_id, **kwargs):
        """Get deposit/depositions/:id/files/:key."""
        try:
            obj = record.files[str(key)].get_version(version_id=version_id)
            return self.make_response(obj=obj or abort(404))
        except KeyError:
            abort(404)

    @require_api_auth()
    @require_oauth_scopes(write_scope.id)
    @pass_record
    @need_record_permission('update_permission_factory')
    def put(self, pid, record, key):
        """Handle PUT deposit files."""
        try:
            data = json.loads(request.data.decode('utf-8'))
            new_key = data['filename']
        except KeyError:
            raise WrongFile()
        new_key_secure = secure_filename(new_key)
        if not new_key_secure or new_key != new_key_secure:
            raise WrongFile()
        try:
            obj = record.files.rename(str(key), new_key_secure)
        except KeyError:
            abort(404)
        record.commit()
        db.session.commit()
        return self.make_response(obj=obj)

    @require_api_auth()
    @require_oauth_scopes(write_scope.id)
    @pass_record
    @need_record_permission('update_permission_factory')
    def delete(self, pid, record, key):
        """Handle DELETE deposit files."""
        try:
            del record.files[str(key)]
            record.commit()
            db.session.commit()
            return make_response('', 204)
        except KeyError:
            abort(404, 'The specified object does not exist or has already '
                  'been deleted.')
