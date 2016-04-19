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
from functools import partial

from flask import current_app, url_for
from flask_login import current_user
from invenio_db import db
from invenio_files_rest.models import Bucket, ObjectVersion
from invenio_jsonschemas.errors import JSONSchemaNotFound
from invenio_pidstore import current_pidstore
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from invenio_records.errors import MissingModelError
from invenio_records.signals import after_record_update, before_record_update
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy

from .minters import deposit_minter
from .models import DepositBucket
from .providers import DepositProvider

current_jsonschemas = LocalProxy(
    lambda: current_app.extensions['invenio-jsonschemas']
)


class Deposit(Record):
    """Define API for changing deposit state."""

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

    @classmethod
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
            data['_deposit']['owners'].append(current_user.get_id())

        return super(Deposit, cls).create(data, id_=id_)

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
                'type': record_pid.pid_type, 'value': record_pid.pid_value
            }

            data = dict(self.dumps())
            data['$schema'] = self.record_schema
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

    def edit(self, pid=None):
        """Edit deposit."""
        pid = pid or self.pid

        if 'published' != self['_deposit']['status']:
            raise PIDInvalidAction()

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

    def discard(self, pid=None):
        """Discard deposit changes."""
        pid = pid or self.pid

        with db.session.begin_nested():
            before_record_update.send(self)

            _, record = self.fetch_published()
            self.model.json = record.model.json
            self.model.json['$schema'] = self.build_deposit_schema(record)

            flag_modified(self.model, 'json')
            db.session.merge(self.model)

        after_record_update.send(self)
        return self.__class__(self.model.json, model=self.model)

    def delete(self, force=True, pid=None):
        """Delete deposit."""
        pid = pid or self.pid

        if self['_deposit']['status'] == 'published' or \
                self['_deposit'].get('pid'):
            raise PIDInvalidAction()
        if pid:
            pid.delete()
        return super(Deposit, self).delete(force=force)

    @property
    def files(self):
        """Get files iterator."""
        if self.model is None:
            raise MissingModelError()

        return FilesIterator(self)


class FileObject(dict):
    """Wrapper for files."""

    def __init__(self, bucket, *args, **kwargs):
        """Bind to current bucket."""
        super(FileObject, self).__init__(*args, **kwargs)
        self.bucket = bucket

    @property
    def obj(self):
        """Return ``ObjectVersion`` instance."""
        return ObjectVersion.get(bucket=self.bucket, **self)

    def get_version(self, version_id=None):
        """Return specific version ``ObjectVersion`` instance or HEAD."""
        return ObjectVersion.get(bucket=self.bucket, key=self['key'],
                                 version_id=version_id)

    def __getattr__(self, key):
        """Proxy to ``obj``."""
        return getattr(self.obj, key)


class FilesIterator(object):
    """Iterator for files."""

    def __init__(self, record):
        """Initialize iterator."""
        self._it = None
        self.record = record
        self.model = record.model

        self.record.setdefault('files', [])

    @property
    def bucket(self):
        """Return file bucket."""
        if not self.model.deposit_bucket:
            self.model.deposit_bucket = DepositBucket(
                bucket=Bucket.create(storage_class=current_app.config[
                    'DEPOSIT_DEFAULT_STORAGE_CLASS'
                ])
            )
        return self.model.deposit_bucket.bucket

    def __len__(self):
        """Get number of files."""
        return len(self.record['files'])

    def __iter__(self):
        """Get iterator."""
        self._it = iter(self.record['files'])
        return self

    def next(self):
        """Python 2.7 compatibility."""
        return self.__next__()  # pragma: no cover

    def __next__(self):
        """Get next file item."""
        return FileObject(self.bucket, next(self._it))

    def __contains__(self, key):
        """Test if file exists."""
        for file_ in self:
            if file_['key'] == key:
                return True
        return False

    def __getitem__(self, key):
        """Get a specific file."""
        for file_ in self.record['files']:
            if file_['key'] == key:
                return FileObject(self.bucket, file_)

        if isinstance(key, int):
            return FileObject(self.bucket, self.record['files'][key])

        raise KeyError(key)

    def __setitem__(self, key, stream):
        """Add file inside a deposit."""
        with db.session.begin_nested():
            # save the file
            obj = ObjectVersion.create(bucket=self.bucket, key=key,
                                       stream=stream)

            # update deposit['files']
            file_ = dict(key=str(obj.key), version_id=str(obj.version_id))
            for index, old in enumerate(self.record['files']):
                if old['key'] == key:
                    self.record['files'][index] = file_
                    break
            else:
                self.record['files'].append(file_)

    def __delitem__(self, key):
        """Delete a file from the deposit."""
        for index, old in enumerate(self):
            if old['key'] == key:
                # delete the object
                obj = ObjectVersion.delete(bucket=self.bucket, key=key)
                del self.record['files'][index]
                return obj
        raise KeyError(key)

    def sort_by(self, *ids):
        """Update files order."""
        keys = dict(zip(ids, range(len(ids))))
        self.record['files'] = list(sorted(
            self.record['files'], key=lambda x: keys[x['key']]
        ))

    def rename(self, old_key, new_key):
        """Rename a file."""
        assert new_key not in self

        for index, file_ in enumerate(self):
            if file_['key'] == old_key:
                # create a new version with the new name
                obj = ObjectVersion.create(
                    bucket=self.bucket, key=new_key,
                    _file_id=file_.obj.file_id
                )
                self.record['files'][index] = dict(
                    key=str(obj.key), version_id=str(obj.version_id)
                )
                # delete the old version
                ObjectVersion.delete(bucket=self.bucket, key=old_key)
                return obj
