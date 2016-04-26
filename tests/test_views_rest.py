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


"""Test deposit workflow."""

from __future__ import absolute_import, print_function

import hashlib
import json
from time import sleep

from flask import url_for
from flask_security import url_for_security
from six import BytesIO

from invenio_deposit.api import Deposit


def test_simple_rest_flow(app, db, es, location, fake_schemas, users):
    """Test simple flow using REST API."""
    app.config['RECORDS_REST_ENDPOINTS']['recid'][
        'read_permission_factory_imp'] = 'invenio_records_rest.utils:allow_all'
    app.config['RECORDS_REST_DEFAULT_READ_PERMISSION_FACTORY'] = \
        'invenio_records_rest.utils:allow_all'

    headers = [('Content-Type', 'application/json'),
               ('Accept', 'application/json')]
    with app.test_request_context():
        with app.test_client() as client:
            # try create deposit as anonymous user (failing)
            res = client.post(url_for('invenio_deposit_rest.dep_list'),
                              data=json.dumps({}), headers=headers)
            assert res.status_code == 401

            # login
            client.post(url_for_security('login'), data=dict(
                email=users[0].email,
                password="tester"
            ))

            # try create deposit as logged in user
            res = client.post(url_for('invenio_deposit_rest.dep_list'),
                              data=json.dumps({}), headers=headers)
            assert res.status_code == 201

            data = json.loads(res.data.decode('utf-8'))
            deposit = data['metadata']
            links = data['links']

            sleep(1)

            # Upload first file:
            content = b'# Hello world!\nWe are here.'
            digest = 'md5:{0}'.format(hashlib.md5(content).hexdigest())
            filename = 'test.json'
            real_filename = 'real_test.json'
            file_to_upload = (BytesIO(content), filename)
            res = client.post(
                links['files'],
                data={'file': file_to_upload, 'name': real_filename},
                content_type='multipart/form-data',
            )
            assert res.status_code == 201
            data = json.loads(res.data.decode('utf-8'))
            file_1 = data['id']

            # Check number of files:
            res = client.get(links['files'])
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert 1 == len(data)

            deposit_1 = dict(**deposit)
            deposit_1['title'] = 'Revision 1'

            res = client.put(links['self'], data=json.dumps(deposit_1),
                             headers=headers)
            data = json.loads(res.data.decode('utf-8'))
            assert res.status_code == 200

            content = b'Second file'
            digest = 'md5:{0}'.format(hashlib.md5(content).hexdigest())
            filename = 'second.json'
            real_filename = 'real_second.json'
            file_to_upload = (BytesIO(content), filename)
            res = client.post(
                links['files'],
                data={'file': file_to_upload, 'name': real_filename},
                content_type='multipart/form-data',
            )
            assert res.status_code == 201
            data = json.loads(res.data.decode('utf-8'))
            file_2 = data['id']

            # Ensure the order:
            res = client.put(links['files'], data=json.dumps([
                {'id': file_1}, {'id': file_2}
            ]))
            assert res.status_code == 200

            # Check number of files:
            res = client.get(links['files'])
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert 2 == len(data)
            assert file_1 == data[0]['id']
            assert file_2 == data[1]['id']

            res = client.post(links['publish'], data=None, headers=headers)
            assert res.status_code == 201

            # Check that the published record is created:
            data = json.loads(res.data.decode('utf-8'))
            deposit_published = data['metadata']
            record_url = url_for(
                'invenio_records_rest.{0}_item'.format(
                    deposit_published['_deposit']['pid']['type']
                ),
                pid_value=deposit_published['_deposit']['pid']['value'],
                _external=True,
            )
            res = client.get(record_url)
            assert res.status_code == 200

            # It should not be possible to delete published deposit:
            res = client.delete(links['self'])
            assert res.status_code == 403
            # or a file:
            res = client.delete(links['files'] + '/' + file_1)
            assert res.status_code == 403

            res = client.post(links['edit'], data=None, headers=headers)
            assert res.status_code == 201

            # It should not be possible to delete previously published deposit:
            res = client.delete(links['self'])
            assert res.status_code == 403
            # or a file:
            res = client.delete(links['files'] + '/' + file_1)
            assert res.status_code == 403

            res = client.put(links['files'], data=json.dumps([
                {'id': file_2}, {'id': file_1}
            ]))
            assert res.status_code == 200

            # Check the order of files:
            res = client.get(links['files'])
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert 2 == len(data)
            assert file_2 == data[0]['id']
            assert file_1 == data[1]['id']

            # After discarding changes the order should be as original:
            res = client.post(links['discard'], data=None, headers=headers)
            assert res.status_code == 201

            # Check the order of files:
            res = client.get(links['files'])
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert 2 == len(data)
            assert file_1 == data[0]['id']
            assert file_2 == data[1]['id']

            # Save new title:
            res = client.patch(links['self'], data=json.dumps([
                    {'op': 'replace', 'path': '/title', 'value': 'Revision 2'},
                ]),
                headers=[('Content-Type', 'application/json-patch+json'),
                         ('Accept', 'application/json')]
            )
            data = json.loads(res.data.decode('utf-8'))
            assert res.status_code == 200

            res = client.post(links['publish'], data=None, headers=headers)
            assert res.status_code == 201

            # Edited record should contain new title:
            res = client.get(record_url)
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert 'Revision 2' == data['metadata']['title']
