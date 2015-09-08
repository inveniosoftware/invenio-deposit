========================
 Invenio-Deposit v0.2.0
========================

Invenio-Deposit v0.2.0 was released on September 8, 2015.

About
-----

Invenio module for depositing metadata using workflows.

*This is an experimental developer preview release.*

Incompatible changes
--------------------

- Removes dependency on bibupload module.
- Removes dependency on legacy bibdocfile module.

New features
------------

- Implements optional JSONSchema-based deposit forms. One can install
  required dependencies using 'invenio_deposit[jsonschema]'.

Improved features
-----------------

- Allows panel headers in form groups to have an icon. Example usage
  {"icon": "fa fa-user"}.

Bug fixes
---------

- Adds missing `invenio_access` dependency and amends past upgrade
  recipes following its separation into standalone package.
- Adds missing dependency to invenio-knowledge package and fixes
  imports.
- Fixes MintedDOIValidator, so that it correctly checks if DOI was
  already minted for the specific upload.

Installation
------------

   $ pip install invenio-deposit==0.2.0

Documentation
-------------

   http://invenio-deposit.readthedocs.org/en/v0.2.0

Happy hacking and thanks for flying Invenio-Deposit.

| Invenio Development Team
|   Email: info@invenio-software.org
|   IRC: #invenio on irc.freenode.net
|   Twitter: http://twitter.com/inveniosoftware
|   GitHub: https://github.com/inveniosoftware/invenio-deposit
|   URL: http://invenio-software.org
