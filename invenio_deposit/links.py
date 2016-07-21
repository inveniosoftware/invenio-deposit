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

"""Links for record serialization."""

from flask import url_for
from invenio_records_files.links import default_bucket_link_factory
from invenio_records_rest.links import default_links_factory


def deposit_links_factory(pid):
    """Factory for record links generation."""
    links = default_links_factory(pid)

    def _url(name, **kwargs):
        """URL builder."""
        endpoint = '.{0}_{1}'.format(pid.pid_type, name)
        return url_for(endpoint, pid_value=pid.pid_value, _external=True,
                       **kwargs)

    links['files'] = _url('files')
    for action in ('publish', 'edit', 'discard'):
        links[action] = _url('actions', action=action)

    bucket_link = default_bucket_link_factory(pid)
    if bucket_link is not None:
        links['bucket'] = bucket_link

    return links
