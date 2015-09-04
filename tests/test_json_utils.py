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

from __future__ import print_function, unicode_literals

from invenio.testsuite import InvenioTestCase, make_test_suite, run_test_suite


class UtilsTest(InvenioTestCase):
    def test_blob(self):
        from invenio_deposit.json_utils import blob2json, json2blob

        json = {
            'key 01': 1,
            'key 02': True,
            'key 03': 1.0,
            'key 04': 'foo',
            'key 05': None,
            'key 06': [1, 2, 3],
            'key 07': {
                'foo': 'bar'
            },
            u'key unicode 👍': u'I enjoyed staying -- באמת! -- at his house.'
        }

        blob = json2blob(json)
        self.assertDictEqual(
            json,
            blob2json(blob),
            'incorrect full serializaion + deserialization'
        )


TEST_SUITE = make_test_suite(UtilsTest)

if __name__ == '__main__':
    run_test_suite(TEST_SUITE)
