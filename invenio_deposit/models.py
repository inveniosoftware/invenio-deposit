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

"""Deposit Models."""

from __future__ import absolute_import

from invenio_db import db
from invenio_files_rest.models import Bucket
from invenio_records.models import RecordMetadata
from sqlalchemy_utils.types import UUIDType


class DepositBucket(db.Model):
    """Relationship Deposit-Bucket."""

    __tablename__ = 'deposit_bucket'

    deposit_id = db.Column(
        UUIDType,
        db.ForeignKey(RecordMetadata.id),
        primary_key=True,
        nullable=False
    )

    bucket_id = db.Column(
        UUIDType,
        db.ForeignKey(Bucket.id),
        primary_key=True,
        nullable=False
    )

    bucket = db.relationship(Bucket)
