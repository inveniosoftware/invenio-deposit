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

"""Module for depositing record metadata and uploading files."""

from __future__ import absolute_import, print_function

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required
from flask_babelex import lazy_gettext as _
from flask_breadcrumbs import register_breadcrumb
from invenio_db import db
from functools import partial
from invenio_pidstore.resolver import Resolver
from ..api import Deposit
from .rest import deposit_actions

blueprint = Blueprint(
    'invenio_deposit',
    __name__,
    template_folder='../templates',
    static_folder='../static',
    url_prefix='/deposit',
)


@blueprint.route('/')
@login_required
@register_breadcrumb(blueprint, '.', _('Deposit'))
def index():
    """List user deposits."""
    return render_template(
        'invenio_deposit/index.html',
    )


@blueprint.route('/new')
@login_required
def new():
    """Create new deposit."""
    from ..api import Deposit
    deposit = Deposit.create(dict(request.values))
    db.session.commit()
    return redirect(url_for('.edit', deposit_id=deposit['_deposit']['id']))


@blueprint.route('/<deposit_id>')
@login_required
@register_breadcrumb(blueprint, '.edit', _('Edit'))
def edit(deposit_id):
    resolver = Resolver(
        pid_type='deposit', object_type='rec',
        getter=partial(Deposit.get_record, with_deleted=True)
    )
    pid, deposit = resolver.resolve(deposit_id)
    return render_template(
        'invenio_deposit/edit.html',
        pid=pid, deposit=deposit,
    )
