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

import datetime
import os
import shutil
import tempfile
from time import sleep

import pytest
from elasticsearch.exceptions import RequestError
from flask import Flask
from flask_babelex import Babel
from flask_breadcrumbs import Breadcrumbs
from flask_celeryext import FlaskCeleryExt
from flask_cli import FlaskCLI
from flask_oauthlib.provider import OAuth2Provider
from flask_security import login_user
from helpers import fill_oauth2_headers, make_pdf_fixture
from invenio_accounts import InvenioAccounts
from invenio_accounts.views import blueprint as accounts_blueprint
from invenio_assets import InvenioAssets
from invenio_db import db as db_
from invenio_db import InvenioDB
from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Location
from invenio_indexer import InvenioIndexer
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_oauth2server import InvenioOAuth2Server, InvenioOAuth2ServerREST
from invenio_oauth2server.models import Client, Token
from invenio_oauth2server.views import \
    settings_blueprint as oauth2server_settings_blueprint
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records_rest import InvenioRecordsREST
from invenio_records_rest.utils import PIDConverter
from invenio_search import InvenioSearch, current_search, current_search_client
from six import BytesIO
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_deposit import InvenioDeposit, InvenioDepositREST
from invenio_deposit.api import Deposit
from invenio_deposit.scopes import write_scope


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
        WTF_CSRF_ENABLED=False,
        DEPOSIT_SEARCH_API='/api/search',
        SECURITY_PASSWORD_HASH='plaintext',
        SECURITY_PASSWORD_SCHEMES=['plaintext'],
        SECURITY_DEPRECATED_PASSWORD_SCHEMES=[],
        OAUTHLIB_INSECURE_TRANSPORT=True,
        OAUTH2_CACHE_TYPE='simple',
    )
    app_.url_map.converters['pid'] = PIDConverter
    FlaskCLI(app_)
    Babel(app_)
    FlaskCeleryExt(app_)
    InvenioDB(app_)
    Breadcrumbs(app_)
    InvenioAccounts(app_)
    app_.register_blueprint(accounts_blueprint)
    InvenioAssets(app_)
    InvenioJSONSchemas(app_)
    InvenioSearch(app_)
    InvenioRecords(app_)
    app_.url_map.converters['pid'] = PIDConverter
    InvenioRecordsREST(app_)
    InvenioPIDStore(app_)
    InvenioIndexer(app_)
    InvenioDeposit(app_)
    InvenioFilesREST(app_)
    OAuth2Provider(app_)
    InvenioOAuth2Server(app_)
    InvenioOAuth2ServerREST(app_)
    app_.register_blueprint(oauth2server_settings_blueprint)
    InvenioDepositREST(app_)

    with app_.app_context():
        yield app_

    shutil.rmtree(instance_path)


@pytest.fixture()
def users(app):
    """Create users."""
    with db_.session.begin_nested():
        datastore = app.extensions['security'].datastore
        user1 = datastore.create_user(email='info@inveniosoftware.org',
                                      password='tester', active=True)
        user2 = datastore.create_user(email='test@inveniosoftware.org',
                                      password='tester2', active=True)
    db_.session.commit()
    return [user1, user2]


@pytest.fixture()
def client(app, users):
    """Create client."""
    with db_.session.begin_nested():
        # create resource_owner -> client_1
        client_ = Client(
            client_id='client_test_u1c1',
            client_secret='client_test_u1c1',
            name='client_test_u1c1',
            description='',
            is_confidential=False,
            user=users[0],
            _redirect_uris='',
            _default_scopes='',
        )
        db_.session.add(client_)
    db_.session.commit()
    return client_


@pytest.fixture()
def write_token_user_1(app, client, users):
    """Create token."""
    with db_.session.begin_nested():
        token_ = Token(
            client=client,
            user=users[0],
            access_token='dev_access_1',
            refresh_token='dev_refresh_1',
            expires=datetime.datetime.now() + datetime.timedelta(hours=10),
            is_personal=False,
            is_internal=True,
            _scopes=write_scope.id,
        )
        db_.session.add(token_)
    db_.session.commit()
    return token_


@pytest.fixture()
def write_token_user_2(app, client, users):
    """Create token."""
    with db_.session.begin_nested():
        token_ = Token(
            client=client,
            user=users[1],
            access_token='dev_access_2',
            refresh_token='dev_refresh_2',
            expires=datetime.datetime.now() + datetime.timedelta(hours=10),
            is_personal=False,
            is_internal=True,
            _scopes=write_scope.id,
        )
        db_.session.add(token_)
    db_.session.commit()
    return token_


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


@pytest.yield_fixture()
def es(app):
    """Elasticsearch fixture."""
    try:
        list(current_search.create())
    except RequestError:
        list(current_search.delete(ignore=[404]))
        list(current_search.create(ignore=[400]))
    current_search_client.indices.refresh()
    yield current_search_client
    list(current_search.delete(ignore=[404]))


@pytest.fixture()
def location(app):
    """Create default location."""
    tmppath = tempfile.mkdtemp()
    with db_.session.begin_nested():
        Location.query.delete()
        loc = Location(name='local', uri=tmppath, default=True)
        db_.session.add(loc)
    db_.session.commit()
    return location


@pytest.fixture()
def deposit(app, es, users, location):
    """New deposit with files."""
    record = {
        'title': 'fuu'
    }
    with app.test_request_context():
        login_user(users[0])
        deposit = Deposit.create(record)
        deposit.commit()
        db_.session.commit()
    sleep(2)
    return deposit


@pytest.fixture()
def files(app, es, deposit):
    """Add a file to the deposit."""
    content = b'### Testing textfile ###'
    stream = BytesIO(content)
    key = 'hello.txt'
    deposit.files[key] = stream
    deposit.commit()
    db_.session.commit()
    return list(deposit.files)


@pytest.fixture()
def pdf_file(app):
    """Create a test pdf file."""
    return {'file': make_pdf_fixture('test.pdf'), 'name': 'test.pdf'}


@pytest.fixture()
def pdf_file2(app):
    """Create a test pdf file."""
    return {'file': make_pdf_fixture('test2.pdf', 'test'), 'name': 'test2.pdf'}


@pytest.fixture()
def pdf_file2_samename(app):
    """Create a test pdf file."""
    return {'file': make_pdf_fixture('test2.pdf', 'test same'),
            'name': 'test2.pdf'}


@pytest.fixture()
def json_headers(app):
    """JSON headers."""
    return [('Content-Type', 'application/json'),
            ('Accept', 'application/json')]


@pytest.fixture()
def oauth2_headers_user_1(app, json_headers, write_token_user_1):
    """Authentication headers (with a valid oauth2 token).

    It uses the token associated with the first user.
    """
    return fill_oauth2_headers(json_headers, write_token_user_1)


@pytest.fixture()
def oauth2_headers_user_2(app, json_headers, write_token_user_2):
    """Authentication headers (with a valid oauth2 token).

    It uses the token associated with the second user.
    """
    return fill_oauth2_headers(json_headers, write_token_user_2)
