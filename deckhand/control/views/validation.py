# Copyright 2017 AT&T Intellectual Property.  All other rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from deckhand.control import common


class ViewBuilder(common.ViewBuilder):
    """Model validation API responses as a python dictionary."""

    _collection_name = 'revisions/%s/validations/%s'

    @classmethod
    def list(cls, validations):
        """Gets the list of validations which have been reported for given
        revision.
        """

        return {
            'count': len(validations),
            'results': [
                {
                    'name': v['name'],
                    'status': v['status'],
                    'url': cls._gen_url(v, props=('revision_id', 'id'))
                }
                for v in validations
            ]
        }

    @classmethod
    def show(cls, validation):
        """Gets basic information of a particular validation entry."""
        return {
            'status': validation.get('status'),
            'validator': validation.get('validator')
        }


class EntriesViewBuilder(common.ViewBuilder):
    """Model validation API responses as a python dictionary."""

    _collection_name = 'revisions/%s/validations/%s/entries/%d'

    @classmethod
    def list_entries(cls, entries):
        """Gets the list of validation entry summaries that have been
        POSTed.
        """
        results = []

        for idx, e in enumerate(entries):
            results.append(
                {
                    'id': idx,
                    'status': e['status'],
                    'url': cls._gen_url(e, props=('revision_id', 'id', idx))
                }
            )

        return {
            'count': len(entries),
            'results': results
        }

    @classmethod
    def show_entry(cls, entry):
        """Gets the full details of a particular validation entry, including
        all POSTed error details.
        """
        return {
            'name': entry.get('name'),
            'status': entry.get('status'),
            'createdAt': entry.get('createdAt'),
            'expiresAfter': entry.get('expiresAfter'),
            'errors': entry.get('errors')
        }
