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

import mock

from deckhand.engine import secrets_manager
from deckhand import factories
from deckhand.tests.unit.engine import test_document_layering


class TestDocumentLayeringWithSubstitution(
        test_document_layering.TestDocumentLayering):

    def test_layering_and_substitution_default_scenario(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_GLOBAL_SUBSTITUTIONS_1_": [{
                "dest": {
                    "path": ".c"
                },
                "src": {
                    "schema": "deckhand/Certificate/v1",
                    "name": "example-cert",
                    "path": "."
                }

            }],
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        secrets_factory = factories.DocumentSecretFactory()
        certificate = secrets_factory.gen_test(
            'Certificate', 'cleartext', data={'secret': 'cert-secret'},
            name='example-cert')

        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': 'cert-secret'}

        with mock.patch.object(
                secrets_manager.db_api, 'document_get',
                return_value=certificate, autospec=True) as mock_document_get:
            self._test_layering(documents, site_expected)
        mock_document_get.assert_called_once_with(
            schema=certificate['schema'], name=certificate['metadata']['name'],
            is_secret=True, **{'metadata.layeringDefinition.abstract': False})

    def test_layering_parent_layer_substitution_child_layer_depends_on(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_GLOBAL_SUBSTITUTIONS_1_": [{
                "dest": {
                    "path": ".b"
                },
                "src": {
                    "schema": "deckhand/Certificate/v1",
                    "name": "example-cert",
                    "path": "."
                }

            }],
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        secrets_factory = factories.DocumentSecretFactory()
        certificate = secrets_factory.gen_test(
            'Certificate', 'cleartext', data={'secret': 'cert-secret'},
            name='example-cert')

        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 'cert-secret'}

        with mock.patch.object(
                secrets_manager.db_api, 'document_get',
                return_value=certificate, autospec=True) as mock_document_get:
            self._test_layering(documents, site_expected)
        mock_document_get.assert_called_once_with(
            schema=certificate['schema'], name=certificate['metadata']['name'],
            is_secret=True, **{'metadata.layeringDefinition.abstract': False})
