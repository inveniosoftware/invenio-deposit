# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2013, 2014, 2015 CERN.
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


import idutils
from invenio_records.api import get_record
from werkzeug import MultiDict

from invenio_utils.datacite import DataciteMetadata


#
# General purpose processors
#


def replace_field_data(field_name, getter=None):
    """Return a processor.

    This will replace the given field names value with the value from the field
    where the processor is installed.
    """
    def _inner(form, field, submit=False, fields=None):
        getattr(form, field_name).data = getter(field) if getter else \
            field.data
    return _inner


def set_flag(flag_name):
    """Return processor which will set a given flag on a field."""
    def _inner(form, field, submit=False, fields=None):
        setattr(field.flags, flag_name, True)
    return _inner


#
# PID processors
#
class PidSchemeDetection(object):

    """Detect persistent identifier scheme and store it in another field."""

    def __init__(self, set_field=None):
        self.set_field = set_field

    def __call__(self, form, field, submit=False, fields=None):
        if field.data:
            schemes = idutils.detect_identifier_schemes(field.data)
            if schemes:
                getattr(form, self.set_field).data = schemes[0]
            else:
                getattr(form, self.set_field).data = ''


class PidNormalize(object):

    """Normalize a persistent identifier."""

    def __init__(self, scheme_field=None, scheme=None):
        self.scheme_field = scheme_field
        self.scheme = scheme

    def __call__(self, form, field, submit=False, fields=None):
        scheme = None
        if self.scheme_field:
            scheme = getattr(form, self.scheme_field).data
        elif self.scheme:
            scheme = self.scheme
        else:
            schemes = idutils.detect_identifier_schemes(field.data)
            if schemes:
                scheme = schemes[0]
        if scheme:
            if field.data:
                field.data = idutils.normalize_pid(field.data, scheme=scheme)


#
# DOI-related processors
#

def datacite_dict_mapper(datacite, form, mapping):
    """Map DataCite metadata to form fields based on a mapping."""
    for func_name, field_name in mapping.items():
        setattr(form, field_name, getattr(datacite, func_name)())


class DataCiteLookup(object):

    """Lookup DOI metadata in DataCite.

    But only if DOI is not locally administered.
    """

    def __init__(self, display_info=False, mapping=None,
                 mapping_func=None, exclude_prefix='10.5072'):
        self.display_info = display_info
        self.mapping = mapping or dict(
            get_publisher='publisher',
            get_titles='title',
            get_dates='date',
            get_description='abstract',
        )
        self.mapping_func = mapping_func or datacite_dict_mapper
        self.prefix = exclude_prefix

    def __call__(self, form, field, submit=False, fields=None):
        if not field.errors and field.data \
           and not field.data.startswith(self.prefix + '/'):
            try:
                datacite = DataciteMetadata(field.data)
                if datacite.error:
                    if self.display_info:
                        field.add_message(
                            "DOI metadata could not be retrieved.",
                            state='info'
                        )
                    return
                if self.mapping_func:
                    self.mapping_func(datacite, form, self.mapping)
                    if self.display_info:
                        field.add_message(
                            "DOI metadata successfully imported from "
                            "DataCite.", state='info')
            except Exception:
                # Ignore errors
                pass


datacite_lookup = DataCiteLookup


def record_id_process(form, field, submit=False):
    value = field.data or ''
    if value == "" or value.isspace():
        return

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    if is_number(field.data):
        json_reader = get_record(value)
    else:
        field.add_message("Record id must be a number!", state='error')
        return

    if json_reader is not None:
        webdeposit_json = form.uncook_json(json_reader, {}, value)
        # FIXME: update current json, past self, what do you mean?? :S

        field.add_message('<a href="/record/"' + value +
                          '>Record</a> was loaded successfully',
                          state='info')

        form.process(MultiDict(webdeposit_json))
    else:
        field.add_message("Record doesn't exist", state='info')
