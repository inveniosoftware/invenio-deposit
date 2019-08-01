..
    This file is part of Invenio.
    Copyright (C) 2015-2019 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.



Changes
=======

Version 1.0.0a10 (release 2019-10-02)

- Adds support for ES 5,6 and 7.

Version 1.0.0a9 (release 2017-12-06)

- Refactoring for Invenio 3.

Version 0.2.0 (release 2015-09-08)

- Removes dependency on bibupload module.
- Removes dependency on legacy bibdocfile module.
- Implements optional JSONSchema-based deposit forms. One can install
  required dependencies using 'invenio_deposit[jsonschema]'.
- Allows panel headers in form groups to have an icon. Example usage
  {"icon": "fa fa-user"}.
- Adds missing `invenio_access` dependency and amends past upgrade
  recipes following its separation into standalone package.
- Adds missing dependency to invenio-knowledge package and fixes
  imports.
- Fixes MintedDOIValidator, so that it correctly checks if DOI was
  already minted for the specific upload.

Version 0.1.0 (release 2015-08-14)

- Initial public release.
