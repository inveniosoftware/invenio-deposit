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


"""Module tests."""

from __future__ import absolute_import, print_function

import hashlib
import json

from flask import url_for
from six import BytesIO

from invenio_deposit.api import Deposit


def test_files_get(app, db, deposit, files):
    """Test rest files get."""
    with app.test_request_context():
        with app.test_client() as client:
            res = client.get(
                url_for('invenio_deposit_rest.dep_files',
                        pid_value=deposit['_deposit']['id']))
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert data[0]['checksum'] == files[0].file.checksum
            assert data[0]['filename'] == files[0].key
            assert data[0]['filesize'] == files[0].file.size


def test_files_get_without_files(app, db, deposit):
    """Test rest files get a deposit without files."""
    with app.test_request_context():
        with app.test_client() as client:
            res = client.get(
                url_for('invenio_deposit_rest.dep_files',
                        pid_value=deposit['_deposit']['id']))
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            assert data == []


def test_files_post(app, db, deposit):
    """Post a deposit file."""
    with app.test_request_context():
        with app.test_client() as client:
            real_filename = 'real_test.json'
            # test empty post
            res = client.post(
                url_for('invenio_deposit_rest.dep_files',
                        pid_value=deposit['_deposit']['id']),
                data={'name': real_filename},
                content_type='multipart/form-data'
            )
            assert res.status_code == 400
            # test post
            content = b'### Testing textfile ###'
            digest = 'md5:{0}'.format(hashlib.md5(content).hexdigest())
            filename = 'test.json'
            file_to_upload = (BytesIO(content), filename)
            res = client.post(
                url_for('invenio_deposit_rest.dep_files',
                        pid_value=deposit['_deposit']['id']),
                data={'file': file_to_upload, 'name': real_filename},
                content_type='multipart/form-data'
            )
            deposit_id = deposit.id
            db.session.expunge(deposit.model)
            deposit = Deposit.get_record(deposit_id)
            files = deposit.files
            assert res.status_code == 201
            assert real_filename == files[0].key
            assert digest == files[0].file.checksum
            data = json.loads(res.data.decode('utf-8'))
            obj = files[0]
            assert data['filename'] == obj.key
            assert data['checksum'] == obj.file.checksum
            assert data['id'] == str(obj.file.id)


def test_files_put(app, db, deposit, files):
    """Test put deposit files."""
    with app.test_request_context():
        with app.test_client() as client:
            key0 = files[0].key
            # add new file
            content = b'### Testing textfile 2 ###'
            stream = BytesIO(content)
            key = 'world.txt'
            storage_class = app.config['DEPOSIT_DEFAULT_STORAGE_CLASS']
            deposit.files[key] = stream
            deposit.commit()
            db.session.commit()
            deposit_id = deposit.id
            db.session.expunge(deposit.model)
            deposit = Deposit.get_record(deposit_id)
            files = deposit.files
            assert deposit['files'][0]['key'] == str(key0)
            assert deposit['files'][1]['key'] == str(key)
            res = client.put(
                url_for('invenio_deposit_rest.dep_files',
                        pid_value=deposit['_deposit']['id']),
                data=json.dumps([
                    {'id': key},
                    {'id': key0}
                ])
            )
            db.session.expunge(deposit.model)
            deposit = Deposit.get_record(deposit_id)
            files = deposit.files
            assert len(deposit['files']) == 2
            assert deposit['files'][0]['key'] == str(key)
            assert deposit['files'][1]['key'] == str(key0)
            data = json.loads(res.data.decode('utf-8'))
            assert data[0]['filename'] == str(key)
            assert data[1]['filename'] == str(key0)


def test_file_get(app, db, deposit, files):
    """Test get file."""
    with app.test_request_context():
        with app.test_client() as client:
            res = client.get(url_for(
                'invenio_deposit_rest.dep_file',
                pid_value=deposit['_deposit']['id'],
                key=files[0].key
            ))
            assert res.status_code == 200
            data = json.loads(res.data.decode('utf-8'))
            obj = files[0]
            assert data['filename'] == obj.key
            assert data['checksum'] == obj.file.checksum
            assert data['id'] == str(obj.file.id)


def test_file_get_not_found(app, db, deposit):
    """Test get file."""
    with app.test_request_context():
        with app.test_client() as client:
            res = client.get(url_for(
                'invenio_deposit_rest.dep_file',
                pid_value=deposit['_deposit']['id'],
                key='not_found'
            ))
            assert res.status_code == 404


def test_file_delete(app, db, deposit, files):
    """Test delete file."""
    with app.test_request_context():
        with app.test_client() as client:
            assert deposit.files[files[0].key] is not None
            res = client.delete(url_for(
                'invenio_deposit_rest.dep_file',
                pid_value=deposit['_deposit']['id'],
                key=files[0].key
            ))
            assert res.status_code == 204
            assert res.data == b''
            deposit_id = deposit.id
            db.session.expunge(deposit.model)
            deposit = Deposit.get_record(deposit_id)
            assert files[0].key not in deposit.files


def test_file_put_not_found_bucket_not_exist(app, db, deposit):
    """Test put file and bucket doesn't exist."""
    with app.test_request_context():
        with app.test_client() as client:
            res = client.put(url_for(
                'invenio_deposit_rest.dep_file',
                pid_value=deposit['_deposit']['id'],
                key='not_found'),
                data=json.dumps({'filename': 'foobar'})
            )
            assert res.status_code == 404


def test_file_put_not_found_file_not_exist(app, db, deposit, files):
    """Test put file and file doesn't exist."""
    with app.test_request_context():
        with app.test_client() as client:
            res = client.put(url_for(
                'invenio_deposit_rest.dep_file',
                pid_value=deposit['_deposit']['id'],
                key='not_found'),
                data=json.dumps({'filename': 'foobar'})
            )
            assert res.status_code == 404


def test_file_put(app, db, deposit, files):
    """PUT a deposit file."""
    with app.test_request_context():
        with app.test_client() as client:
            # test rename file
            old_file_id = files[0].file_id
            old_filename = files[0].key
            new_filename = '{0}-new-name'.format(old_filename)
            res = client.put(
                url_for('invenio_deposit_rest.dep_file',
                        pid_value=deposit['_deposit']['id'],
                        key=old_filename),
                data=json.dumps({'filename': new_filename}))
            deposit_id = deposit.id
            db.session.expunge(deposit.model)
            deposit = Deposit.get_record(deposit_id)
            files = deposit.files
            assert res.status_code == 200
            files = deposit.files
            assert new_filename == files[0].key
            assert old_file_id == files[0].file_id
            data = json.loads(res.data.decode('utf-8'))
            obj = files[0]
            assert data['filename'] == obj.key
            assert data['checksum'] == obj.file.checksum
            assert data['id'] == str(obj.file.id)
