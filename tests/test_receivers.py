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

from six import BytesIO


def test_add_file(app, db, deposit, files):
    """Test add file."""
    assert 'files' in deposit
    assert deposit['files'][0]['key'] == str(files[0].key)
    assert deposit['files'][0]['version_id'] == str(files[0].version_id)
    # test add new file
    content = b'### Testing textfile 2 ###'
    stream = BytesIO(content)
    key = "world.txt"
    storage_class = app.config['DEPOSIT_DEFAULT_STORAGE_CLASS']
    obj = deposit.add_file(key=key, stream=stream,
                           storage_class=storage_class)
    db.session.commit()
    assert len(deposit['files']) == 2
    assert deposit['files'][1]['key'] == key
    assert obj.key == key


def test_no_file(app, db, deposit):
    """Test rest files get."""
    assert 'files' in deposit
    assert len(deposit['files']) == 0


def test_rename_file(app, db, deposit, files):
    """Test rename file."""
    old_filename = files[0].key
    new_filename = "{0}-new-name".format(old_filename)
    deposit.rename_file(old_key=old_filename, new_key=new_filename)
    db.session.commit()
    files = deposit.get_files()
    assert deposit['files'][0]['key'] == str(new_filename)
    assert deposit['files'][0]['version_id'] == str(files[0].version_id)


def test_delete_file(app, db, deposit, files):
    """Test delete file."""
    deposit.delete_file(key=files[0].key)
    db.session.commit()
    assert len(deposit['files']) == 0


def test_order_files(app, db, deposit, files):
    """Test add file."""
    key0 = files[0].key
    # add new file
    content = b'### Testing textfile 2 ###'
    stream = BytesIO(content)
    key = "world.txt"
    storage_class = app.config['DEPOSIT_DEFAULT_STORAGE_CLASS']
    deposit.add_file(key=key, stream=stream,
                     storage_class=storage_class)
    db.session.commit()
    assert len(deposit['files']) == 2
    assert deposit['files'][0]['key'] == str(key0)
    assert deposit['files'][1]['key'] == str(key)
    deposit.update_file_order(
        [deposit['files'][1]['key'], deposit['files'][0]['key']])
    assert len(deposit['files']) == 2
    assert deposit['files'][0]['key'] == str(key)
    assert deposit['files'][1]['key'] == str(key0)
