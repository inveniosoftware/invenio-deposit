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

"""Record field function."""

from __future__ import absolute_import, print_function


def deposit_list_files_update(record, **kwargs):
    """Update deposit['files'] when record insert/update."""
    from .api import Deposit
    if 'files' not in record:
        # init files
        record['files'] = [
            {
                "key": str(obj.key),
                "version_id": str(obj.version_id)
            } for obj in Deposit(record).get_files()
        ]


def deposit_add_file(deposit, obj):
    """Update deposit['files'] after new file is created."""
    deposit['files'].append({
        "key": str(obj.key),
        "version_id": str(obj.version_id)
    })
    deposit.commit()


def deposit_rename_file(deposit, old_obj, new_obj):
    """Update deposit['files'] after filename change."""
    for obj in deposit['files']:
        if obj['key'] == str(old_obj.key):
            obj['key'] = str(new_obj.key)
            obj['version_id'] = str(new_obj.version_id)
            deposit.commit()
            return


def deposit_delete_file(deposit, old_key):
    """Update deposit['files'] when a file is deleted."""
    for (index, obj) in enumerate(deposit['files']):
        if obj['key'] == str(old_key):
            del deposit['files'][index]
            deposit.commit()
            return


def deposit_get_files_ordered(deposit):
    """Get files ordered."""
    return deposit['files']


def deposit_update_files_order(deposit, ids):
    """Save new order."""
    ordered = []
    for id_ in ids:
        for (index, obj) in enumerate(deposit['files']):
            if obj['key'] == id_:
                ordered.append(deposit['files'].pop(index))
    deposit['files'] = ordered
    deposit.commit()
