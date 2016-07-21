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

import pytest
from flask import Flask, render_template_string
from flask_cli import FlaskCLI
from invenio_records_rest.utils import PIDConverter

from invenio_deposit import InvenioDeposit, bundles
from invenio_deposit.proxies import current_deposit


def _check_template():
    """Check template."""
    extended = """
        {% extends 'invenio_deposit/edit.html' %}
        {% block javascript %}{% endblock %}
        {% block css %}{% endblock %}
        {% block page_body %}{{ super() }}{% endblock %}
    """
    rendered = render_template_string(
        extended,
        pid=dict(pid_value=None),
        record=dict()
    )

    assert 'invenio-records' in rendered
    assert 'invenio-records-alert' in rendered
    assert 'invenio-records-form' in rendered
    assert 'invenio-records-actions' in rendered
    assert 'invenio-files-uploader' in rendered
    assert 'invenio-files-upload-zone' in rendered
    assert 'invenio-files-list' in rendered


def test_version():
    """Test version import."""
    from invenio_deposit import __version__
    assert __version__


def test_bundles():
    """Test bundles."""
    assert bundles.js
    assert bundles.js_dependecies


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    FlaskCLI(app)
    app.url_map.converters['pid'] = PIDConverter
    ext = InvenioDeposit(app)
    assert 'invenio-deposit' in app.extensions

    app = Flask('testapp')
    FlaskCLI(app)
    app.url_map.converters['pid'] = PIDConverter

    # check that current_deposit cannot be resolved
    with app.app_context():
        with pytest.raises(KeyError):
            current_deposit.init_app

    ext = InvenioDeposit()
    assert 'invenio-deposit' not in app.extensions
    ext.init_app(app)
    assert 'invenio-deposit' in app.extensions

    # check that current_deposit resolves correctly
    with app.app_context():
        current_deposit.init_app


def test_view(app):
    """Test view."""
    with app.test_request_context():
        _check_template()
