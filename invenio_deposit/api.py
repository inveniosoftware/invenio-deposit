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

"""Deposit API."""

import uuid

from flask import current_app, url_for
from invenio_db import db
from invenio_pidstore import current_pidstore
from invenio_records.api import Record
from jsonpatch import apply_patch
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy

from .minters import deposit_minter


class Deposit(Record):
    """Define API for changing deposit state."""

    @classmethod
    def create(cls, data, id_=None):
        """Create a deposit."""
        id_ = id_ or uuid.uuid4()
        pid = deposit_minter(id_, data)
        # TODO check valid JSON schemas
        data.setdefault('$schema', url_for(
            'invenio_jsonschemas.get_schema',
            schema_path='deposits/deposit-v1.0.0.json',
            _external=True,
        ))
        return super(Deposit, cls).create(data, id_=id_)

    def publish(self, pid=None, id_=None):
        """Publish a deposit."""

        id_ = id_ or uuid.uuid4()
        # TODO check valid JSON schemas
        data = dict(self)
        schema = data.pop('$schema', None)
        # TODO make it configurable
        minter = current_pidstore.minters['recid']
        pid = minter(id_, data)

        self['_deposit']['status'] = 'published'
        self['_deposit']['pid'] = {
            'type': pid.pid_type, 'value': pid.pid_value
        }
        record = Record.create(data, id_=id_)
        self.commit()
        return record

    def edit(self, pid=None):
        """Edit deposit."""
        # TODO check for valid statuses?
        # TODO change schema
        self['_deposit']['status'] = 'draft'
        self.commit()

    def discard(self, pid=None):
        """Discard deposit."""
        if self['_deposit']['status'] == 'published' or \
                self['_deposit'].get('pid'):
            raise AlreadyPublished()
        if pid:
            pid.delete()
        self.delete(force=True)
