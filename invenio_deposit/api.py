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
from contextlib import contextmanager
from functools import partial, wraps

from elasticsearch.exceptions import RequestError
from flask import current_app
from flask_login import current_user
from invenio_db import db
from invenio_files_rest.models import Bucket
from invenio_indexer.api import RecordIndexer
from invenio_jsonschemas.errors import JSONSchemaNotFound
from invenio_pidstore import current_pidstore
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_pidstore.resolver import Resolver
from invenio_records.signals import after_record_update, before_record_update
from invenio_records_files.api import Record
from invenio_records_files.models import RecordsBuckets
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.local import LocalProxy

from .minters import deposit_minter
from .providers import DepositProvider

current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


def index(method=None, delete=False):
    """Update index."""
    if method is None:
        return partial(index, delete=delete)

    @wraps(method)
    def wrapper(self_or_cls, *args, **kwargs):
        """Send record for indexing."""
        result = method(self_or_cls, *args, **kwargs)
        try:
            if delete:
                self_or_cls.indexer.delete(result)
            else:
                self_or_cls.indexer.index(result)
        except RequestError:
            current_app.logger.exception('Could not index {0}.'.format(result))
        return result
    return wrapper


def has_status(method=None, status='draft'):
    """Check that deposit has defined status (default: draft)."""
    if method is None:
        return partial(has_status, status=status)

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        """Check current deposit status."""
        if status != self['_deposit']['status']:
            raise PIDInvalidAction()

        return method(self, *args, **kwargs)
    return wrapper


class Deposit(Record):
    """Define API for changing deposit state."""

    indexer = RecordIndexer()
    """Default deposit indexer."""

    @property
    def pid(self):
        """Return an instance of deposit PID."""
        return PersistentIdentifier.get(DepositProvider.pid_type,
                                        self['_deposit']['id'])

    @property
    def record_schema(self):
        """Convert deposit schema to a valid record schema."""
        schema_path = current_jsonschemas.url_to_path(self['$schema'])
        schema_prefix = current_app.config['DEPOSIT_JSONSCHEMAS_PREFIX']
        if schema_path and schema_path.startswith(schema_prefix):
            return current_jsonschemas.path_to_url(
                schema_path[len(schema_prefix):]
            )

    def build_deposit_schema(self, record):
        """Convert record schema to a valid deposit schema."""
        schema_path = current_jsonschemas.url_to_path(record['$schema'])
        schema_prefix = current_app.config['DEPOSIT_JSONSCHEMAS_PREFIX']
        if schema_path:
            return current_jsonschemas.path_to_url(
                schema_prefix + schema_path
            )

    def fetch_published(self):
        """Return a tuple with PID and published record."""
        pid_type = self['_deposit']['pid']['type']
        pid_value = self['_deposit']['pid']['value']

        resolver = Resolver(
            pid_type=pid_type, object_type='rec',
            getter=partial(Record.get_record, with_deleted=True)
        )
        return resolver.resolve(pid_value)

    def merge_with_published(self):
        """."""
        # TODO if revisions are the same then we can apply directly
        # latest = self.fetch_published()
        # initial = A.revisions[self['_deposit']['pid']['revision']]
        # patch = diff(initial, self)
        # latest.apply(patch)

    @index
    def commit(self, *args, **kwargs):
        """Store changes on current instance in database."""
        return super(Deposit, self).commit(*args, **kwargs)

    @classmethod
    @index
    def create(cls, data, id_=None):
        """Create a deposit."""
        data.setdefault('$schema', current_jsonschemas.path_to_url(
            current_app.config['DEPOSIT_DEFAULT_JSONSCHEMA']
        ))
        if not current_jsonschemas.url_to_path(data['$schema']):
            raise JSONSchemaNotFound(data['$schema'])
        if '_deposit' not in data:
            id_ = id_ or uuid.uuid4()
            deposit_minter(id_, data)

        data['_deposit'].setdefault('owners', list())
        if current_user and current_user.is_authenticated:
            creator_id = int(current_user.get_id())

            if creator_id not in data['_deposit']['owners']:
                data['_deposit']['owners'].append(creator_id)

            data['_deposit']['created_by'] = creator_id

        return super(Deposit, cls).create(data, id_=id_)

    # No need for indexing as it calls self.commit()
    @has_status
    def publish(self, pid=None, id_=None):
        """Publish a deposit."""
        pid = pid or self.pid

        if not pid.is_registered():
            raise PIDInvalidAction()

        self['_deposit']['status'] = 'published'

        if self['_deposit'].get('pid') is None:  # First publishing
            minter = current_pidstore.minters[
                current_app.config['DEPOSIT_PID_MINTER']
            ]
            id_ = id_ or uuid.uuid4()
            record_pid = minter(id_, self)

            self['_deposit']['pid'] = {
                'type': record_pid.pid_type, 'value': record_pid.pid_value,
                'revision_id': 0,
            }

            data = dict(self.dumps())
            data['$schema'] = self.record_schema

            # During first publishing create snapshot the bucket.
            @contextmanager
            def process_files(data):
                """Process deposit files."""
                if self.files and self.files.bucket:
                    assert not self.files.bucket.locked
                    self.files.bucket.locked = True
                    snapshot = self.files.bucket.snapshot(lock=True)
                    data['_files'] = self.files.dumps(bucket=snapshot.id)
                    yield data
                    db.session.add(RecordsBuckets(
                        record_id=id_, bucket_id=snapshot.id
                    ))
                else:
                    yield data

            with process_files(data) as data:
                record = Record.create(data, id_=id_)
        else:  # Update after edit
            record_pid, record = self.fetch_published()
            # TODO add support for patching
            assert record.revision_id == self['_deposit']['pid']['revision_id']

            data = dict(self.dumps())
            data['$schema'] = self.record_schema
            record = record.__class__(data, model=record.model)
            record.commit()

        self.commit()
        return self

    @has_status(status='published')
    @index
    def edit(self, pid=None):
        """Edit deposit."""
        pid = pid or self.pid

        def _edit(record):
            """Update selected keys."""
            data = record.dumps()
            # Keep current record revision for merging.
            data['_deposit']['pid']['revision_id'] = record.revision_id
            data['_deposit']['status'] = 'draft'
            data['$schema'] = self.build_deposit_schema(record)
            return data

        with db.session.begin_nested():
            before_record_update.send(self)

            record_pid, record = self.fetch_published()
            assert PIDStatus.REGISTERED == record_pid.status
            assert record['_deposit'] == self['_deposit']

            self.model.json = _edit(record)

            flag_modified(self.model, 'json')
            db.session.merge(self.model)

        after_record_update.send(self)
        return self.__class__(self.model.json, model=self.model)

    @has_status
    @index
    def discard(self, pid=None):
        """Discard deposit changes."""
        pid = pid or self.pid

        with db.session.begin_nested():
            before_record_update.send(self)

            _, record = self.fetch_published()
            self.model.json = record.model.json
            self.model.json['_deposit']['status'] = 'draft'
            self.model.json['$schema'] = self.build_deposit_schema(record)

            flag_modified(self.model, 'json')
            db.session.merge(self.model)

        after_record_update.send(self)
        return self.__class__(self.model.json, model=self.model)

    @has_status
    @index(delete=True)
    def delete(self, force=True, pid=None):
        """Delete deposit."""
        pid = pid or self.pid

        if self['_deposit'].get('pid'):
            raise PIDInvalidAction()
        if pid:
            pid.delete()
        return super(Deposit, self).delete(force=force)

    @has_status
    def clear(self, *args, **kwargs):
        """Clear only drafts."""
        _deposit = self['_deposit']
        super(Deposit, self).clear(*args, **kwargs)
        self['_deposit'] = _deposit

    @has_status
    def update(self, *args, **kwargs):
        """Update only drafts."""
        _deposit = self['_deposit']
        super(Deposit, self).update(*args, **kwargs)
        self['_deposit'] = _deposit

    @has_status
    def patch(self, *args, **kwargs):
        """Patch only drafts."""
        _deposit = self['_deposit']
        patched = super(Deposit, self).patch(*args, **kwargs)
        patched['_deposit'] = _deposit
        return patched

    def _create_bucket(self):
        """Override bucket creation."""
        return Bucket.create(storage_class=current_app.config[
            'DEPOSIT_DEFAULT_STORAGE_CLASS'
        ])

    @property
    def files(self):
        """Add validation on ``sort_by`` method."""
        files_ = super(Deposit, self).files

        if files_:
            sort_by_ = files_.sort_by

            def sort_by(*args, **kwargs):
                """Only in draft state."""
                if 'draft' != self['_deposit']['status']:
                    raise PIDInvalidAction()
                return sort_by_(*args, **kwargs)

            files_.sort_by = sort_by

        return files_
