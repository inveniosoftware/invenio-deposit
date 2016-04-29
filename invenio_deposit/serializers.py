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

"""Deposit serializers."""

import json

from flask import Response, jsonify, make_response


def json_serializer(pid, data, *args):
    """Build a JSON Flask response using the given data.

    :returns: A Flask response with JSON data.
    :returns type: :py:class:`flask.Response`
    """
    if data is not None:
        response = Response(
            json.dumps(data.dumps()),
            mimetype='application/json'
        )
    else:
        response = Response(mimetype='application/json')
    # response.set_etag(str(data.model.version_id))
    return response


def file_serializer(obj):
    """Serialize a object."""
    return {
        "id": str(obj.file_id),
        "filename": obj.key,
        "filesize": obj.file.size,
        "checksum": obj.file.checksum,
    }


def json_file_serializer(obj, status=None):
    """JSON File Serializer."""
    return make_response(jsonify(file_serializer(obj)), status)


def json_files_serializer(objs, status=None):
    """JSON Files Serializer."""
    files = [file_serializer(obj) for obj in objs]
    return make_response(json.dumps(files), status)


def json_file_response(obj, status=None):
    """JSON Files/File serializer."""
    from invenio_records_files.api import FilesIterator

    if isinstance(obj, FilesIterator):
        return json_files_serializer(objs=obj, status=status)
    else:
        return json_file_serializer(obj=obj, status=status)


json_v1_files_response = json_file_response
