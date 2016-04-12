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
from invenio_records.signals import after_record_update, before_record_update
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy

from .minters import deposit_minter
from .models import DepositBucket
from .providers import DepositProvider
from .receivers import deposit_add_file, deposit_rename_file, \
    deposit_delete_file, deposit_get_files_ordered, deposit_update_files_order

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

        if current_user and current_user.is_authenticated:
            data['_deposit'].setdefault('owners', list())
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

    def add_file(self, key, stream, location=None, storage_class=None):
        """Add new file inside a deposit."""
        with db.session.begin_nested():
            # get the bucket
            try:
                bucket = self.get_bucket()
            except NoResultFound:
                # if doesn't exist, create it
                bucket = Bucket.create(location=location,
                                       storage_class=storage_class)
                # and connect to the deposit
                dbucket = DepositBucket(deposit_id=self.id,
                                        bucket_id=bucket.id)
                db.session.add(dbucket)

            # save the file
            obj = ObjectVersion.create(bucket=bucket, key=key, stream=stream)

            # update deposit['files']
            deposit_add_file(self, obj)

        return obj

    def rename_file(self, old_key, new_key):
        """Rename a file."""
        bucket = self.get_bucket()
        obj = self.get_file(key=old_key)
        if not obj:
            raise NoResultFound("{0} not found", old_key)
        # create a new version with the new name
        new_obj = ObjectVersion.create(bucket=bucket, key=new_key,
                                       _file_id=obj.file_id)
        # update deposit['files']
        deposit_rename_file(self, obj, new_obj)
        # delete the old version
        ObjectVersion.delete(bucket=bucket, key=obj.key)
        return new_obj

    def get_files(self):
        """Get files."""
        try:
            # get the Bucket
            bucket = self.get_bucket()
            # get the list of files
            objs = ObjectVersion.get_by_bucket(bucket).all()
            # order files
            ordered = []
            for f in deposit_get_files_ordered(self):
                for (index, obj) in enumerate(objs):
                    if f['key'] == obj.key:
                        ordered.append(objs.pop(index))
            return ordered
        except NoResultFound:
            return []

    def get_file(self, key, version_id=None):
        """Get a file."""
        # get the Bucket
        bucket = self.get_bucket()
        # serialize the file
        return ObjectVersion.get(
            bucket=bucket, key=key, version_id=version_id)

    def delete_file(self, key):
        """Delete a file from the deposit."""
        try:
            # get the Bucket
            bucket = self.get_bucket()
            # delete the object
            new_obj = ObjectVersion.delete(bucket=bucket, key=key)
            # update deposit['files']
            deposit_delete_file(self, old_key=key)
            return new_obj
        except NoResultFound:
            return False

    def get_bucket(self):
        """Get bucket."""
        return DepositBucket.query.filter_by(
            deposit_id=self.id).one().bucket

    def update_file_order(self, ids):
        """Update files order."""
        deposit_update_files_order(self, ids)
