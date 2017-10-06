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

from deckhand.engine import document_validation
from deckhand import errors
from deckhand import factories
from deckhand.tests.unit.engine import base as engine_test_base


class TestDocumentValidation(engine_test_base.TestDocumentValidationBase):

    def test_init_document_validation(self):
        self._read_data('sample_document')
        doc_validation = document_validation.DocumentValidation(
            self.data)
        self.assertIsInstance(doc_validation,
                              document_validation.DocumentValidation)

    def test_data_schema_missing_optional_sections(self):
        self._read_data('sample_data_schema')
        optional_missing_data = [
            self._corrupt_data('metadata.labels'),
        ]

        for missing_data in optional_missing_data:
            document_validation.DocumentValidation(missing_data).validate_all()

    def test_document_missing_optional_sections(self):
        self._read_data('sample_document')
        properties_to_remove = (
            'metadata.layeringDefinition.actions',
            'metadata.layeringDefinition.parentSelector',
            'metadata.substitutions',
            'metadata.substitutions.2.dest.pattern')

        for property_to_remove in properties_to_remove:
            optional_data_removed = self._corrupt_data(property_to_remove)
            document_validation.DocumentValidation(
                optional_data_removed).validate_all()

    @mock.patch.object(document_validation, 'LOG', autospec=True)
    def test_abstract_document_not_validated(self, mock_log):
        self._read_data('sample_document')
        # Set the document to abstract.
        updated_data = self._corrupt_data(
            'metadata.layeringDefinition.abstract', True, op='replace')
        # Guarantee that a validation error is thrown by removing a required
        # property.
        del updated_data['metadata']['layeringDefinition']['layer']

        document_validation.DocumentValidation(updated_data).validate_all()
        self.assertTrue(mock_log.info.called)
        self.assertIn("Skipping schema validation for abstract document",
                      mock_log.info.mock_calls[0][1][0])


class TestDocumentDebugging(engine_test_base.TestDocumentValidationBase):

    def setUp(self):
        super(TestDocumentDebugging, self).setUp()
        mock_uuid = mock.patch.object(
            document_validation, 'uuidutils').start()
        mock_uuid.generate_uuid.return_value = 'test'

        mock.patch.object(document_validation, 'db_api').start()

    def _validate_errors(self, validation_docs, exceptions,
                         expected_debug_section, expected_exc):
        # Validate correct number of documents returned.
        self.assertEqual(2, len(validation_docs))

        debug_doc = validation_docs[0]
        validation_doc = validation_docs[1]

        from pprint import pprint

        pprint(debug_doc)

        # Validate debug document.
        if 'schema' in expected_debug_section:
            self.assertEqual('deckhand/Debug/v1', debug_doc['schema'])
        self.assertIn('debug', debug_doc)
        self.assertEqual(expected_debug_section, debug_doc['debug'])

        # Validate validation policy.
        self.assertEqual('deckhand/ValidationPolicy/v1',
                         validation_doc['schema'])
        self.assertEqual('deckhand-schema-validation',
                         validation_doc['metadata']['name'])
        self.assertEqual(
            'failure', validation_doc['data']['validations'][0]['status'])

        # Validate exception was thrown.
        self.assertEqual(1, len(exceptions))
        self.assertIsInstance(exceptions[0], expected_exc)

    def test_all_missing_sections(self):
        validation_docs, exceptions = document_validation.DocumentValidation(
            {}).validate_all()
        expected_debug_section = {
            'data': '[test] This required field is missing or invalid.',
            'metadata': {
                'name': '[test] This required field is missing or invalid.',
                'schema': '[test] This required field is missing or invalid.'
            },
            'schema': ("[test] This required field is missing or invalid.")
        }
        self._validate_errors(
            validation_docs, exceptions, expected_debug_section,
            expected_exc=errors.InvalidDocumentFormat)

    def test_schema_missing_section(self):
        validation_docs, exceptions = document_validation.DocumentValidation(
            {'data': {}, 'metadata': {}}).validate_all()
        expected_debug_section = {
            'metadata': {
                'name': '[test] This required field is missing or invalid.',
                'schema': '[test] This required field is missing or invalid.'
            },
            'schema': ("[test] This required field is missing or invalid.")
        }
        self._validate_errors(
            validation_docs, exceptions, expected_debug_section,
            expected_exc=errors.InvalidDocumentFormat)

    def test_metadata_missing_section(self):
        validation_docs, exceptions = document_validation.DocumentValidation(
            {'data': {}, 'schema': 'test/test/v1'}).validate_all()
        expected_debug_section = {
            'metadata': {
                'name': '[test] This required field is missing or invalid.',
                'schema': '[test] This required field is missing or invalid.'
            }
        }
        self._validate_errors(
            validation_docs, exceptions, expected_debug_section,
            expected_exc=errors.InvalidDocumentFormat)

    def test_data_missing_section(self):
        validation_docs, exceptions = document_validation.DocumentValidation(
            {'metadata': {}, 'schema': 'test/test/v1'}).validate_all()
        expected_debug_section = {
            'data': '[test] This required field is missing or invalid.',
            'metadata': {
                'name': '[test] This required field is missing or invalid.',
                'schema': '[test] This required field is missing or invalid.'
            }
        }
        self._validate_errors(
            validation_docs, exceptions, expected_debug_section,
            expected_exc=errors.InvalidDocumentFormat)

    def test_data_with_wrong_type(self):
        validation_docs, exceptions = document_validation.DocumentValidation(
            {'schema': 5}).validate_all()
        expected_debug_section = {
            'data': '[test] This required field is missing or invalid.',
            'metadata': {
                'name': '[test] This required field is missing or invalid.',
                'schema': '[test] This required field is missing or invalid.'
            },
            'schema': ("[test] This field has the wrong type. Given: int, "
                       "required: ['string'].")
        }
        self._validate_errors(
            validation_docs, exceptions, expected_debug_section,
            expected_exc=errors.InvalidDocumentFormat)

    def test_pass_base_schema_with_invalid_schema(self):
        secrets_factory = factories.DocumentSecretFactory()
        certificate = secrets_factory.gen_test(
            'Certificate', 'cleartext', 'secret')
        certificate['schema'] = 'foo/bar/v1'

        validation_docs, exceptions = document_validation.DocumentValidation(
            certificate).validate_all()
        expected_debug_section = {
            'schema': '[test] This required field is missing or invalid.'
        }
        self._validate_errors(
            validation_docs, exceptions, expected_debug_section,
            expected_exc=errors.InvalidDocumentSchema)
