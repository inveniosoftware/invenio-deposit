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

"""Module for depositing record metadata and uploading files."""

from __future__ import absolute_import, print_function

from . import config
from .cli import deposit as cmd
from .receivers import index_deposit_after_publish
from .signals import post_action
from .views import rest, ui


class InvenioDeposit(object):
    """Invenio-Deposit extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization.

        Initialize the CLI and all UI endpoints.
        Connect all signals if `DEPOSIT_REGISTER_SIGNALS` is ``True``.

        :param app: An instance of :class:`flask.Flask`.
        """
        self.init_config(app)
        app.cli.add_command(cmd)
        app.register_blueprint(ui.create_blueprint(
            app.config['DEPOSIT_RECORDS_UI_ENDPOINTS']
        ))
        app.extensions['invenio-deposit'] = self
        if app.config['DEPOSIT_REGISTER_SIGNALS']:
            post_action.connect(index_deposit_after_publish, sender=app,
                                weak=False)

    def init_config(self, app):
        """Initialize configuration.

        :param app: An instance of :class:`flask.Flask`.
        """
        app.config.setdefault(
            'DEPOSIT_BASE_TEMPLATE',
            app.config.get('BASE_TEMPLATE',
                           'invenio_deposit/base.html'))
        for k in dir(config):
            if k.startswith('DEPOSIT_'):
                app.config.setdefault(k, getattr(config, k))


class InvenioDepositREST(object):
    """Invenio-Deposit REST extension."""

    def __init__(self, app=None):
        """Extension initialization.

        :param app: An instance of :class:`flask.Flask`.
        """
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization.

        Initialize the CLI and all REST endpoints.
        Connect all signals if `DEPOSIT_REGISTER_SIGNALS` is True.

        :param app: An instance of :class:`flask.Flask`.
        """
        self.init_config(app)
        app.register_blueprint(rest.create_blueprint(
            app.config['DEPOSIT_REST_ENDPOINTS']
        ))
        app.extensions['invenio-deposit-rest'] = self
        if app.config['DEPOSIT_REGISTER_SIGNALS']:
            post_action.connect(index_deposit_after_publish, sender=app,
                                weak=False)

    def init_config(self, app):
        """Initialize configuration.

        :param app: An instance of :class:`flask.Flask`.
        """
        for k in dir(config):
            if k.startswith('DEPOSIT_'):
                app.config.setdefault(k, getattr(config, k))
