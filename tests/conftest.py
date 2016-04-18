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


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from flask import Flask
from flask_celeryext import FlaskCeleryExt
from flask_cli import FlaskCLI
from invenio_db import db as db_
from invenio_db import InvenioDB
from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Location
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records_rest import InvenioRecordsREST
from invenio_search import InvenioSearch
from six import BytesIO
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_deposit import InvenioDeposit, InvenioDepositREST
from invenio_deposit.api import Deposit


@pytest.yield_fixture()
def app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()
    app_ = Flask(__name__, instance_path=instance_path)
    app_.config.update(
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND='memory',
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND='cache',
        SECRET_KEY='CHANGE_ME',
        SECURITY_PASSWORD_SALT='CHANGE_ME_ALSO',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        TESTING=True,
    )
    FlaskCLI(app_)
    FlaskCeleryExt(app_)
    InvenioDB(app_)
    InvenioJSONSchemas(app_)
    InvenioSearch(app_)
    InvenioRecords(app_)
    InvenioRecordsREST(app_)
    InvenioPIDStore(app_)
    InvenioDeposit(app_)
    InvenioFilesREST(app_)
    InvenioDepositREST(app_)

    with app_.app_context():
        yield app_

    shutil.rmtree(instance_path)


@pytest.yield_fixture()
def db(app):
    """Database fixture."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.fixture()
def fake_schemas(app, tmpdir):
    """Fake schema."""
    schemas = tmpdir.mkdir('schemas')
    empty_schema = '{"title": "Empty"}'
    for path in (('deposit-v1.0.0.json', ),
                 ('deposits', 'test-v1.0.0.json'),
                 ('test-v1.0.0.json', ), ):
        schema = schemas
        for section in path[:-1]:
            schema = schema.mkdir(section)
        schema = schema.join(path[-1])
        schema.write(empty_schema)

    app.extensions['invenio-jsonschemas'].register_schemas_dir(schemas.strpath)


@pytest.fixture()
def location(app):
    """Create default location."""
    tmppath = tempfile.mkdtemp()
    with db_.session.begin_nested():
        Location.query.delete()
        loc = Location(name='local', uri=tmppath, default=True)
        db_.session.add(loc)
    db_.session.commit()


@pytest.fixture()
def deposit(app, location):
    """New deposit with files."""
    record = {
        "title": "fuu"
    }
    deposit = Deposit.create(record)
    db_.session.commit()
    return deposit


@pytest.fixture()
def files(app, deposit):
    """Add a file to the deposit."""
    content = b'### Testing textfile ###'
    stream = BytesIO(content)
    key = "hello.txt"
    storage_class = app.config['DEPOSIT_DEFAULT_STORAGE_CLASS']
    obj = deposit.add_file(key=key, stream=stream,
                           storage_class=storage_class)
    db_.session.commit()
    return [obj]
