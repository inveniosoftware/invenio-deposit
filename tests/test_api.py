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

"""Test the API."""

from __future__ import absolute_import, print_function

import pytest
from invenio_jsonschemas.errors import JSONSchemaNotFound
from invenio_pidstore.errors import PIDInvalidAction
from sqlalchemy.orm.exc import NoResultFound

from invenio_deposit.api import Deposit


def test_schemas(app, db, fake_schemas):
    """Test schema URL transformations."""
    deposit = Deposit.create({})
    assert 'http://localhost/schemas/deposits/deposit-v1.0.0.json' == \
        deposit['$schema']

    assert 'http://localhost/schemas/deposit-v1.0.0.json' == \
        deposit.record_schema

    assert 'http://localhost/schemas/deposits/test-v1.0.0.json' == \
        deposit.build_deposit_schema({
            '$schema': 'http://localhost/schemas/test-v1.0.0.json',
        })

    with pytest.raises(JSONSchemaNotFound):
        Deposit.create({
            '$schema': 'http://localhost/schemas/deposits/invalid.json',
        })


def test_simple_flow(app, db, fake_schemas):
    """Test simple flow of deposit states through its lifetime."""
    deposit = Deposit.create({})
    assert deposit['_deposit']['id']
    assert 'draft' == deposit['_deposit']['status']
    assert 0 == deposit.revision_id

    deposit.publish()
    assert 'published' == deposit['_deposit']['status']
    assert 1 == deposit.revision_id

    with pytest.raises(PIDInvalidAction):
        deposit.delete()
    assert 'published' == deposit['_deposit']['status']

    deposit = deposit.edit()
    assert 'draft' == deposit['_deposit']['status']
    assert 2 == deposit.revision_id
    assert 0 == deposit['_deposit']['pid']['revision_id']

    with pytest.raises(PIDInvalidAction):
        deposit.edit()
    assert 'draft' == deposit['_deposit']['status']

    deposit['title'] = 'Revision 1'
    deposit.publish()
    assert 'published' == deposit['_deposit']['status']
    assert 3 == deposit.revision_id
    assert 0 == deposit['_deposit']['pid']['revision_id']

    deposit = deposit.edit()
    assert 'draft' == deposit['_deposit']['status']
    assert 4 == deposit.revision_id
    assert 1 == deposit['_deposit']['pid']['revision_id']

    deposit['title'] = 'Revision 2'
    deposit.commit()
    assert 5 == deposit.revision_id

    deposit = deposit.discard()
    assert 'Revision 1' == deposit['title']
    assert 6 == deposit.revision_id


def test_delete(app, db, fake_schemas):
    """Test simple delete."""
    deposit = Deposit.create({})
    pid = deposit.pid
    assert deposit['_deposit']['id']
    assert 'draft' == deposit['_deposit']['status']
    assert 0 == deposit.revision_id

    deposit.delete()

    with pytest.raises(NoResultFound):
        Deposit.get_record(deposit.id)

    with pytest.raises(PIDInvalidAction):
        deposit.publish(pid=pid)
