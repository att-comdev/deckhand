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

# Generic schema used to validate all documents.
schema = {
    'type': 'object',
    'properties': {
        'schema': {
            'type': 'string',
            # Currently supported versions include v1 only.
            'pattern': '^([A-Za-z\-\_]+\/[A-Za-z\-\_]+\/v[1]{1}\.[0]{1})$'
        },
        'metadata': {
            'type': 'object',
            'properties': {
                'schema': {'type': 'string'},
                'name': {'type': 'string'}
            },
            'additionalProperties': True,
            'required': ['schema', 'name']
        },
        'data': {'type': ['string', 'object']}
    },
    'additionalProperties': False,
    # NOTE(fmontei): All schemas require the "data" section except for
    # Tombstone documents. Since this is a generic schema for validating all
    # documents, we omit "data" below as all documents are subject to more
    # fine-grained schema validation anyway.
    'required': ['schema', 'metadata']
}
