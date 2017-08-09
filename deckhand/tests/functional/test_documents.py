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

import os
import yaml

import falcon

from deckhand.control import api
from deckhand.engine import document_validation
from deckhand.tests.functional import base as test_base
from deckhand import types


class TestDocumentsApi(test_base.TestFunctionalBase):

    DATABASE_ATTRS = ('name', 'deleted', 'created_at', 'updated_at',
                      'revision_id', 'deleted_at', 'id')

    def _read_test_resource(self, file_name):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_yaml_path = os.path.abspath(os.path.join(
            dir_path, os.pardir, 'unit', 'resources', file_name + '.yaml'))

        with open(test_yaml_path, 'r') as yaml_file:
            yaml_data = yaml_file.read()
        return yaml_data

    def test_create_document(self):
        yaml_data = self._read_test_resource('sample_document')
        expected_documents = [yaml.safe_load(yaml_data)]

        # Validate that document creation works.
        result = self.app.simulate_post('/api/v1.0/documents', body=yaml_data)
        self.assertEqual(falcon.HTTP_201, result.status)
        self.assertIsNotNone(result.text)

        # Validate that the correct number of documents were created: one
        # document corresponding to ``yaml_data``.
        resp_documents = [d for d in yaml.safe_load_all(result.text)]
        self.assertIsInstance(resp_documents, list)
        self.assertEqual(1, len(resp_documents))

        # Validate that the expected database attributes are included in the
        # response body. Remove them afterward so that document pre-validation
        # succeeds.
        for attr in self.DATABASE_ATTRS:
            self.assertIn(attr, resp_documents[0])
            del resp_documents[0][attr]

        # Validate that the original key-value pairs are identical.
        self.assertEqual(expected_documents, resp_documents)

        # Validate that the document, minus the additional database attributes,
        # conforms to schema validation.
        doc_validation = document_validation.DocumentValidation(resp_documents)
        doc_validation.validate_all()

    def test_delete_document(self):
        # Create a document.
        yaml_data = self._read_test_resource('sample_document')
        result = self.app.simulate_post('/api/v1.0/documents', body=yaml_data)
        resp_documents = [d for d in yaml.safe_load_all(result.text)]
        document_id = resp_documents[0]['id']

        # Validate that document deletion works.
        result = self.app.simulate_delete(
            '/api/v1.0/documents/%s' % document_id)
        self.assertEqual(falcon.HTTP_204, result.status)
        self.assertEmpty(result.text)
