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

import collections

from deckhand.control import common
from deckhand import types
from deckhand import utils


class ViewBuilder(common.ViewBuilder):
    """Model validation API responses as a python dictionary."""

    _collection_name = 'validations'

    def list(self, validations):
        # Retain the original ordering of the DB (to preserve ordering of
        # ``entry_id``s).
        validation_map = collections.OrderedDict()
        for v in validations:
            validation_map.setdefault(v['name'], 'success')
            if v['status'] == 'failure':
                validation_map[v['name']] = 'failure'

        return {
            'count': len(validation_map),
            'results': [
                {'name': k, 'status': v} for k, v in validation_map.items() 
            ]
        }

    def list_entries(self, entries):
        results = []

        for idx, e in enumerate(entries):
            results.append({'status': e['status'], 'id': idx})

        return {
            'count': len(entries),
            'results': results
        }

    def show(self, validation):
        return {
            'status': validation.get('status'),
            'validator': validation.get('validator')
        }

    def show_entry(self, entry):
        return {
            'name': entry.get('name'),
            'status': entry.get('status'),
            'createdAt': entry.get('createdAt'),
            'expiresAfter': entry.get('expiresAfter'),
            'errors': entry.get('errors')
        }
