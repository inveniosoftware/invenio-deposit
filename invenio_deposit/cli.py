# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""Click command-line interface for record management."""

from __future__ import absolute_import, print_function

import json
import sys
import uuid

import click
import pkg_resources
from flask import current_app
from flask_cli import with_appcontext
from invenio_db import db
from invenio_pidstore import current_pidstore
from sqlalchemy import exc

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest


def process_minter(value):
    """Load minter from PIDStore registry based on given value."""
    try:
        return current_pidstore.minters[value]
    except KeyError:
        raise click.BadParameter(
            'Unknown minter {0}. Please use one of {1}.'.format(
                value, ', '.join(current_pidstore.minters.keys())
            )
        )


def process_schema(value):
    """Load schema from JSONSchema registry based on given value."""
    schemas = current_app.extensions['invenio-jsonschemas'].schemas
    try:
        return schemas[value]
    except KeyError:
        raise click.BadParameter(
            'Unknown schema {0}. Please use one of:\n {1}'.format(
                value, '\n'.join(schemas.keys())
            )
        )

option_pid_minter = click.option('--pid-minter', multiple=True,
                                    default=None)


#
# Deposit management commands
#
@click.group()
def deposit():
    """Deposit management commands."""


@deposit.command()
@click.argument('source')
@with_appcontext
def schema(source):
    """Create deposit schema from an existing schema."""
    click.echo(process_schema(source))
    # TODO



@deposit.command()
@click.argument('source', type=click.File('r'), default=sys.stdin)
@click.option('-i', '--id', 'ids', multiple=True)
@click.option('--force', is_flag=True, default=False)
@option_pid_minter
@with_appcontext
def create(source, ids, force, pid_minter=None):
    """Create new bibliographic record(s)."""
    # Make sure that all imports are done with application context.
    from .api import Record
    from .models import RecordMetadata

    pid_minter = [process_minter(minter) for minter in pid_minter or []]

    data = json.load(source)

    if isinstance(data, dict):
        data = [data]

    if ids:
        assert len(ids) == len(data), 'Not enough identifiers.'

    for record, id_ in zip_longest(data, ids):
        id_ = id_ or uuid.uuid4()
        for minter in pid_minter:
            minter(id_, record)

        click.echo(Record.create(record, id_=id_).id)
    db.session.commit()


@deposit.command()
@click.option('-i', '--id', 'ids', multiple=True)
def publish(ids):
    """Publish selected deposits."""


@deposit.command()
@click.option('-i', '--id', 'ids', multiple=True)
def edit(ids):
    """Make selected deposits editable."""


@deposit.command()
@click.option('-i', '--id', 'ids', multiple=True)
def discard(ids):
    """Discard selected deposits."""
