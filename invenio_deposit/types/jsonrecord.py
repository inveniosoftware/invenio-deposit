# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Simple test workflow for JSON-schema based deposits."""

from .simplerecord import SimpleRecordDeposition

__all__ = ['JsonRecordDeposition']


class JsonRecordDeposition(SimpleRecordDeposition):

    """Submit a simple JSON record."""

    @classmethod
    def process_sip_metadata(cls, deposition, metadata):
        """Map keywords to match jsonalchemy configuration."""
        if '_json' in metadata:
            json = metadata.pop('_json')

            json['$schema'] = json['$schema'].replace(
                '/forms',
                '/records'
            )

            for k, v in json.iteritems():
                # FIXME what to do with conflicts?
                metadata[k] = v
