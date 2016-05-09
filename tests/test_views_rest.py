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

import json
from time import sleep

import pytest
from flask import url_for
from flask_security import url_for_security
from six import BytesIO


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 401),
    # owner
    (dict(email='info@invenio-software.org', password='tester'), 200),
    # user that not have permissions
    (dict(email='test@invenio-software.org', password='tester2'), 403),
])
def test_edit_deposit_users(app, db, es, users, location, deposit,
                            json_headers, user_info, status):
    """Test edit deposit by the owner."""
    deposit_id = deposit['_deposit']['id']
    with app.test_request_context():
        with app.test_client() as client:
            if user_info:
                # login
                res = client.post(url_for_security('login'), data=user_info)
            res = client.put(
                url_for('invenio_deposit_rest.dep_item', pid_value=deposit_id),
                data=json.dumps({"title": "bar"}),
                headers=json_headers
            )
            assert res.status_code == status


def test_edit_deposit_by_good_oauth2_token(app, db, es, users, location,
                                           deposit, write_token_user_1,
                                           oauth2_headers_user_1):
    """Test edit deposit with a correct oauth2 token."""
    deposit_id = deposit['_deposit']['id']
    with app.test_request_context():
        # with oauth2
        with app.test_client() as client:
            res = client.put(
                url_for('invenio_deposit_rest.dep_item', pid_value=deposit_id),
                data=json.dumps({"title": "bar"}),
                headers=oauth2_headers_user_1
            )
            assert res.status_code == 200


def test_edit_deposit_by_bad_oauth2_token(app, db, es, users, location,
                                          deposit, write_token_user_2,
                                          oauth2_headers_user_2):
    """Test edit deposit with a wrong oauth2 token."""
    deposit_id = deposit['_deposit']['id']
    with app.test_request_context():
        # with oauth2
        with app.test_client() as client:
            res = client.put(
                url_for('invenio_deposit_rest.dep_item', pid_value=deposit_id),
                data=json.dumps({"title": "bar"}),
                headers=oauth2_headers_user_2
            )
            assert res.status_code == 403


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 401),
    # owner
    (dict(email='info@invenio-software.org', password='tester'), 204),
    # user that not have permissions
    (dict(email='test@invenio-software.org', password='tester2'), 403),
])
def test_delete_deposit_users(app, db, es, users, location, deposit,
                              json_headers, user_info, status):
    """Test delete deposit by users."""
    deposit_id = deposit['_deposit']['id']
    with app.test_request_context():
        with app.test_client() as client:
            if user_info:
                # login
                res = client.post(url_for_security('login'), data=user_info)
            res = client.delete(
                url_for('invenio_deposit_rest.dep_item', pid_value=deposit_id),
                data=json.dumps({"title": "bar"}),
                headers=json_headers
            )
            assert res.status_code == status


def test_delete_deposit_by_good_oauth2_token(app, db, es, users, location,
                                             deposit, write_token_user_1,
                                             oauth2_headers_user_1):
    """Test delete deposit with a good oauth2 token."""
    deposit_id = deposit['_deposit']['id']
    with app.test_request_context():
        # with oauth2
        with app.test_client() as client:
            res = client.delete(
                url_for('invenio_deposit_rest.dep_item', pid_value=deposit_id),
                data=json.dumps({"title": "bar"}),
                headers=oauth2_headers_user_1
            )
            assert res.status_code == 204


def test_delete_deposit_by_bad_oauth2_token(app, db, es, users, location,
                                            deposit, write_token_user_2,
                                            oauth2_headers_user_2):
    """Test delete deposit with a bad oauth2 token."""
    deposit_id = deposit['_deposit']['id']
    with app.test_request_context():
        # with oauth2
        with app.test_client() as client:
            res = client.delete(
                url_for('invenio_deposit_rest.dep_item', pid_value=deposit_id),
                data=json.dumps({"title": "bar"}),
                headers=oauth2_headers_user_2
            )
            assert res.status_code == 403


def test_simple_rest_flow(app, db, es, location, fake_schemas, users,
                          json_headers):
    """Test simple flow using REST API."""
    app.config['RECORDS_REST_ENDPOINTS']['recid'][
        'read_permission_factory_imp'] = 'invenio_records_rest.utils:allow_all'
    app.config['RECORDS_REST_DEFAULT_READ_PERMISSION_FACTORY'] = \
        'invenio_records_rest.utils:allow_all'

    with app.test_request_context():
        with app.test_client() as client:
            # try create deposit as anonymous user (failing)
            res = client.post(url_for('invenio_deposit_rest.dep_list'),
                              data=json.dumps({}), headers=json_headers)
            assert res.status_code == 401

            # login
            client.post(url_for_security('login'), data=dict(
                email=users[0].email,
                password="tester"
            ))

            # try create deposit as logged in user
            res = client.post(url_for('invenio_deposit_rest.dep_list'),
                              data=json.dumps({}), headers=json_headers)
            assert res.status_code == 201

            data = json.loads(res.data.decode('utf-8'))
            deposit = data['metadata']
            links = data['links']

            sleep(1)

            # Upload first file:
            content = b'# Hello world!\nWe are here.'
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
                             headers=json_headers)
            data = json.loads(res.data.decode('utf-8'))
            assert res.status_code == 200

            content = b'Second file'
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

            res = client.post(links['publish'], data=None,
                              headers=json_headers)
            assert res.status_code == 202

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

            res = client.post(links['edit'], data=None, headers=json_headers)
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
            res = client.post(links['discard'], data=None,
                              headers=json_headers)
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

            res = client.post(links['publish'], data=None,
                              headers=json_headers)
            assert res.status_code == 202

            # Edited record should contain new title:
            res = client.get(record_url)
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert 'Revision 2' == data['metadata']['title']
