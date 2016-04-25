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


"""Minimal Flask application example for development.

Installation proccess
---------------------

First preapare all static files:

.. code-block:: console

   $ cd examples
   $ npm install -g node-sass clean-css requirejs uglify-js
   $ pip install -r requirements.txt
   $ flask -a app.py npm
   $ cd static ; npm install ; cd ..
   $ flask -a app.py collect -v
   $ flask -a app.py assets build

Make sure that ``elasticsearch`` server is running:

.. code-block:: console

   $ elasticsearch

   ... version[2.0.0] ...

Create demo records

.. code-block:: console

   $ mkdir instance
   $ flask -a app.py db init
   $ flask -a app.py db create
   $ flask -a app.py index init
   $ flask -a app.py users create info@inveniosoftware.org --password 123456 -a
   $ flask -a app.py fixtures records

Start the server

.. code-block:: console

   $ flask -a app.py --debug run

Visit your favorite browser on `http://localhost:5000/search
<http://localhost:5000/deposit>`_.

"""

from __future__ import absolute_import, print_function

import os
from os.path import dirname, join

import jinja2
from flask import Flask, current_app
from flask_babelex import Babel
from flask_cli import FlaskCLI, with_appcontext
from invenio_accounts import InvenioAccounts
from invenio_accounts.views import blueprint as accounts_blueprint
from invenio_admin import InvenioAdmin
from invenio_assets import InvenioAssets
from invenio_db import InvenioDB, db
from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Location
from invenio_indexer import InvenioIndexer
from invenio_indexer.api import RecordIndexer
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_oauth2server import InvenioOAuth2Server
from invenio_oauth2server.views import server_blueprint, settings_blueprint
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records_rest import InvenioRecordsREST
from invenio_records_rest.facets import terms_filter
from invenio_records_ui import InvenioRecordsUI
from invenio_rest import InvenioREST
from invenio_search import InvenioSearch
from invenio_search_ui import InvenioSearchUI
from invenio_search_ui.bundles import js
from invenio_theme import InvenioTheme

from invenio_deposit import InvenioDeposit, InvenioDepositREST

# Create Flask application
app = Flask(__name__)

app.config.update(
    CELERY_ALWAYS_EAGER=True,
    CELERY_CACHE_BACKEND='memory',
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_RESULT_BACKEND='cache',
    JSONSCHEMAS_HOST='localhost:5000',
    REST_ENABLE_CORS=True,
    SECRET_KEY='changeme',
    SERVER_NAME='localhost:5000',
    SQLALCHEMY_TRACK_MODIFICATIONS=True,
    DEPOSIT_SEARCH_API='/deposits',
    RECORDS_REST_FACETS=dict(
        deposits=dict(
            aggs=dict(
                status=dict(terms=dict(
                    field='_deposit.status'
                )),
            ),
            post_filters=dict(
                status=terms_filter(
                    '_deposit.status'
                ),
            )
        )
    ),
    RECORDS_UI_DEFAULT_PERMISSION_FACTORY=None,
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI',
                                      'sqlite:///app.db'),
    DATADIR=join(dirname(__file__), 'data/upload'),
    OAUTH2SERVER_CACHE_TYPE='simple',
    OAUTHLIB_INSECURE_TRANSPORT=True,
)

FlaskCLI(app)
Babel(app)

# Set jinja loader to first grab templates from the app's folder.
app.jinja_loader = jinja2.ChoiceLoader([
    jinja2.FileSystemLoader(join(dirname(__file__), "templates")),
    app.jinja_loader
])

InvenioDB(app)
InvenioTheme(app)
InvenioJSONSchemas(app)
InvenioAccounts(app)
InvenioRecords(app)
InvenioRecordsUI(app)
search = InvenioSearch(app)
# search.register_mappings('testrecords', 'data')
InvenioSearchUI(app)
InvenioREST(app)
InvenioIndexer(app)
InvenioPIDStore(app)
InvenioAdmin(app)
InvenioOAuth2Server(app)

InvenioRecordsREST(app)
InvenioFilesREST(app)

assets = InvenioAssets(app)
assets.env.register('invenio_search_ui_search_js', js)

InvenioDeposit(app)
InvenioDepositREST(app)

app.register_blueprint(accounts_blueprint)

app.register_blueprint(settings_blueprint)
app.register_blueprint(server_blueprint)


@app.cli.group()
def fixtures():
    """Command for working with test data."""


@fixtures.command()
@with_appcontext
def records():
    """Load records."""
    import pkg_resources
    from dojson.contrib.marc21 import marc21
    from dojson.contrib.marc21.utils import create_record, split_blob
    from flask_login import login_user, logout_user
    from invenio_accounts.models import User
    from invenio_deposit.api import Deposit

    users = User.query.all()

    # pkg resources the demodata
    data_path = pkg_resources.resource_filename(
        'invenio_records', 'data/marc21/bibliographic.xml'
    )
    with open(data_path) as source:
        with current_app.test_request_context():
            indexer = RecordIndexer()
            with db.session.begin_nested():
                for index, data in enumerate(split_blob(source.read()),
                                             start=1):
                    login_user(users[index % len(users)])
                    # do translate
                    record = marc21.do(create_record(data))
                    # create record
                    indexer.index(Deposit.create(record))
                    logout_user()
            db.session.commit()


@fixtures.command()
@with_appcontext
def location():
    """Load default location."""
    d = current_app.config['DATADIR']
    with db.session.begin_nested():
        Location.query.delete()
        loc = Location(name='local', uri=d, default=True)
        db.session.add(loc)
    db.session.commit()
