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
from functools import partial, wraps

from elasticsearch.exceptions import RequestError
from flask import current_app, url_for
from flask_login import current_user
from invenio_db import db
from invenio_files_rest.models import Bucket, ObjectVersion
from invenio_indexer.api import RecordIndexer
from invenio_jsonschemas.errors import JSONSchemaNotFound
from invenio_pidstore import current_pidstore
from invenio_pidstore.errors import PIDInvalidAction
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from invenio_records.errors import MissingModelError
from invenio_records.signals import after_record_update, before_record_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy

from .minters import deposit_minter
from .models import DepositBucket
from .providers import DepositProvider
from .utils import sorted_files_from_bucket

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
        owner = getattr(current_user, 'id', 0)
        if owner not in data['_deposit']['owners']:
            data['_deposit']['owners'].append(owner)

        return super(Deposit, cls).create(data, id_=id_)

    # No need for indexing as it calls self.commit()
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
            assert 'snapshot' not in self['_deposit']
            if self.files.bucket:
                self['_deposit']['snapshot'] = str(
                    self.files.bucket.snapshot(lock=True).id
                )
                # TODO move to before record create signal handler?
                data['files'] = self.files.dumps(
                    bucket=self['_deposit']['snapshot']
                )

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

    @index
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

    @index
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

    @index(delete=True)
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


class FileObject(object):
    """Wrapper for files."""

    def __init__(self, bucket, obj):
        """Bind to current bucket."""
        self.obj = obj
        self.bucket = bucket

    def get_version(self, version_id=None):
        """Return specific version ``ObjectVersion`` instance or HEAD."""
        return ObjectVersion.get(bucket=self.bucket, key=self.obj.key,
                                 version_id=version_id)

    def __getattr__(self, key):
        """Proxy to ``obj``."""
        return getattr(self.obj, key)

    def __getitem__(self, key):
        """Proxy to ``obj``."""
        return getattr(self.obj, key)


def _not_published(method):
    """Check that record is in defined status."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        """Send record for indexing."""
        if 'published' == self.record['_deposit']['status'] or \
                'pid' in self.record['_deposit']:
            raise PIDInvalidAction()
        return method(self, *args, **kwargs)
    return wrapper


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
            try:
                self.model.deposit_bucket = DepositBucket(
                    bucket=Bucket.create(storage_class=current_app.config[
                        'DEPOSIT_DEFAULT_STORAGE_CLASS'
                    ])
                )
            except IntegrityError:
                current_app.logger.exception('Check default location.')
                return None
        return self.model.deposit_bucket.bucket

    @property
    def keys(self):
        """Return file keys."""
        return [file_['key'] for file_ in self.record['files']]

    def __len__(self):
        """Get number of files."""
        return ObjectVersion.get_by_bucket(self.bucket).count()

    def __iter__(self):
        """Get iterator."""
        self._it = iter(sorted_files_from_bucket(
            self.bucket, self.keys
        ))
        return self

    def next(self):
        """Python 2.7 compatibility."""
        return self.__next__()  # pragma: no cover

    def __next__(self):
        """Get next file item."""
        obj = next(self._it)
        return FileObject(self.bucket, obj)

    def __contains__(self, key):
        """Test if file exists."""
        return ObjectVersion.get_by_bucket(
            self.bucket).filter_by(key=str(key)).count()

    def __getitem__(self, key):
        """Get a specific file."""
        obj = ObjectVersion.get(self.bucket, key)
        if obj:
            return FileObject(self.bucket, obj)
        raise KeyError(key)

    @_not_published
    def __setitem__(self, key, stream):
        """Add file inside a deposit."""
        with db.session.begin_nested():
            # save the file
            obj = ObjectVersion.create(bucket=self.bucket, key=key,
                                       stream=stream)

            # update deposit['files']
            if key not in self.record['files']:
                self.record['files'].append({'key': key})

    @_not_published
    def __delitem__(self, key):
        """Delete a file from the deposit."""
        obj = ObjectVersion.delete(bucket=self.bucket, key=key)
        self.record['files'] = [file_ for file_ in self.record['files']
                                if file_['key'] != key]
        if obj is None:
            raise KeyError(key)

    def sort_by(self, *ids):
        """Update files order."""
        files = {str(f_.file_id): f_.key for f_ in self}
        self.record['files'] = [{'key': files.get(id_, id_)} for id_ in ids]

    @_not_published
    def rename(self, old_key, new_key):
        """Rename a file."""
        assert new_key not in self

        file_ = self[old_key]
        # create a new version with the new name
        obj = ObjectVersion.create(
            bucket=self.bucket, key=new_key,
            _file_id=file_.obj.file_id
        )
        self.record['files'][self.keys.index(old_key)]['key'] = new_key
        # delete the old version
        ObjectVersion.delete(bucket=self.bucket, key=old_key)
        return obj

    def dumps(self, bucket=None):
        """Serialize files from a bucket."""
        return [{
            'bucket': str(file_.bucket_id),
            'checksum': file_.file.checksum,
            'key': file_.key,  # IMPORTANT it must stay here!
            'size': file_.file.size,
            'version_id': str(file_.version_id),
        } for file_ in sorted_files_from_bucket(
            bucket or self.bucket, self.keys
        )]
