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

"""Different utils for JSON handling."""

import base64
import json


def json2blob(j):
    """Convert JSON object (dict) into a base64 blob.

    The blob format is the following:

    .. code-block::

        base64 encoded data:
            UTF8 encoded string:
                stringified JSON
    """
    if j:
        return base64.b64encode(json.dumps(j).encode('utf8'))
    else:
        return ""


def blob2json(b):
    """Convert base64 into a JSON object (dict).

    See :func:`json2blob` for an explanation about the blob format.
    """
    s = base64.b64decode(b).decode('utf8').strip()
    if s:
        return json.loads(s)
    else:
        return None
