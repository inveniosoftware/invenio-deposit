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

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'invenio-accounts>=1.0.0a9',
    'isort>=4.2.2',
    'psycopg2>=2.6.1',
    'pydocstyle>=1.0.0',
    'pytest-cache>=1.0',
    'pytest-cov>=1.8.0',
    'pytest-pep8>=1.0.6',
    'pytest>=2.8.0',
    'reportlab>=3.3.0',
]

extras_require = {
    'docs': [
        'Sphinx>=1.4.2',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup_requires = [
    'Babel>=1.3',
    'pytest-runner>=2.6.2',
]

install_requires = [
    'Flask-BabelEx>=0.9.2',
    'Flask-Login>=0.3.2',
    'SQLAlchemy-Continuum>=1.2.1',
    'SQLAlchemy-Utils[encrypted]>=0.31.0',
    'dictdiffer>=0.5.0.post1',
    'elasticsearch-dsl>=2.0.0',
    'invenio-db[versioning]>=1.0.0a9',
    'invenio-files-rest>=1.0.0a4',
    'invenio-indexer>=1.0.0a2',
    'invenio-jsonschemas>=1.0.0a3',
    'invenio-oauth2server>=1.0.0a5',
    'invenio-records-files>=1.0.0a4',
    'invenio-records-rest>=1.0.0a13',
    'invenio-records-ui>=1.0.0a6',
    'invenio-records>=1.0.0a15',
    'invenio-search-ui>=1.0.0a4',
    'invenio-search>=1.0.0a7',
]

packages = find_packages()


# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('invenio_deposit', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='invenio-deposit',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio deposit upload',
    license='GPLv2',
    author='CERN',
    author_email='info@inveniosoftware.org',
    url='https://github.com/inveniosoftware/invenio-deposit',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'invenio_base.apps': [
            'invenio_deposit = invenio_deposit:InvenioDeposit',
        ],
        'invenio_base.api_apps': [
            'invenio_deposit_rest = invenio_deposit:InvenioDepositREST',
        ],
        'invenio_access.actions': [
            'deposit_admin_access'
            ' = invenio_deposit.permissions:action_admin_access',
        ],
        'invenio_assets.bundles': [
            'invenio_deposit_js = invenio_deposit.bundles:js',
            'invenio_deposit_css = invenio_deposit.bundles:css',
        ],
        'invenio_i18n.translations': [
            'messages = invenio_deposit',
        ],
        'invenio_pidstore.fetchers': [
            'deposit = invenio_deposit.fetchers:deposit_fetcher',
        ],
        'invenio_pidstore.minters': [
            'deposit = invenio_deposit.minters:deposit_minter',
        ],
        'invenio_jsonschemas.schemas': [
            'deposits = invenio_deposit.jsonschemas',
        ],
        'invenio_search.mappings': [
            'deposits = invenio_deposit.mappings',
        ],
        'invenio_oauth2server.scopes': [
            'deposit_write = invenio_deposit.scopes:write_scope',
            'deposit_actions = invenio_deposit.scopes:actions_scope',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 1 - Planning',
    ],
)
