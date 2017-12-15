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
from deckhand.tests.unit.engine import base as test_base
from deckhand import types


class TestDocumentValidationNegative(test_base.TestDocumentValidationBase):
    """Negative testing suite for document validation."""

    # The 'data' key is mandatory but not critical if excluded.
    exception_map = {
        'metadata': errors.InvalidDocumentFormat,
        'metadata.schema': errors.InvalidDocumentFormat,
        'metadata.name': errors.InvalidDocumentFormat,
        'schema': errors.InvalidDocumentFormat,
    }

    def setUp(self):
        super(TestDocumentValidationNegative, self).setUp()
        # Stub out the DB call for retrieving DataSchema documents.
        self.patchobject(document_validation.db_api, 'revision_get_documents',
                         lambda *a, **k: [])

    def _do_validations(self, document_validator, expected, expected_err):
        validations = document_validator.validate_all()
        self.assertEqual(2, len(validations))
        # The DataSchema document itself should've validated
        # successfully.
        self.assertEqual('success', validations[0]['status'])
        self.assertEqual('failure', validations[-1]['status'])
        self.assertEqual({'version': '1.0', 'name': 'deckhand'},
                         validations[-1]['validator'])
        self.assertEqual(types.DECKHAND_SCHEMA_VALIDATION,
                         validations[-1]['name'])
        self.assertEqual(1, len(validations[-1]['errors']))
        self.assertEqual(expected['metadata']['name'],
                         validations[-1]['errors'][-1]['name'])
        self.assertEqual(expected['schema'],
                         validations[-1]['errors'][-1]['schema'])
        self.assertEqual(expected_err,
                         validations[-1]['errors'][-1]['message'])

    def _test_missing_required_sections(self, document, properties_to_remove):
        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(document, property_to_remove)

            exception_raised = self.exception_map.get(property_to_remove, None)
            expected_err_msg = "'%s' is a required property" % missing_prop

            dataschema_factory = factories.DataSchemaFactory()
            dataschema = dataschema_factory.gen_test(
                invalid_data.get('schema', ''), {})
            payload = [dataschema, invalid_data]

            doc_validator = document_validation.DocumentValidation(payload)
            if exception_raised:
                self.assertRaises(
                    exception_raised, doc_validator.validate_all)
            else:
                self._do_validations(doc_validator, invalid_data,
                                     expected_err_msg)

    def test_certificate_key_missing_required_sections(self):
        document = self._read_data('sample_certificate_key')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data', 'metadata.storagePolicy',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_certificate_missing_required_sections(self):
        document = self._read_data('sample_certificate')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data', 'metadata.storagePolicy',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_data_schema_missing_required_sections(self):
        document = self._read_data('sample_data_schema')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data', 'data.$schema',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_document_missing_required_sections(self):
        document = self._read_data('sample_document')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data',
            'metadata.layeringDefinition',
            'metadata.layeringDefinition.layer',
            'metadata.layeringDefinition.actions.0.method',
            'metadata.layeringDefinition.actions.0.path',
            'metadata.substitutions.0.dest',
            'metadata.substitutions.0.dest.path',
            'metadata.substitutions.0.src',
            'metadata.substitutions.0.src.schema',
            'metadata.substitutions.0.src.name',
            'metadata.substitutions.0.src.path')
        self._test_missing_required_sections(document, properties_to_remove)

    def test_document_invalid_layering_definition_action(self):
        document = self._read_data('sample_document')
        missing_data = self._corrupt_data(
            document, 'metadata.layeringDefinition.actions.0.method',
            'invalid', op='replace')
        expected_err = "'invalid' is not one of ['replace', 'delete', 'merge']"

        # Ensure that a dataschema document exists for the random document
        # schema via mocking.
        dataschema_factory = factories.DataSchemaFactory()
        dataschema = dataschema_factory.gen_test(document['schema'], {})
        payload = [dataschema, missing_data]
        doc_validator = document_validation.DocumentValidation(payload)
        self._do_validations(doc_validator, document, expected_err)

    def test_layering_policy_missing_required_sections(self):
        document = self._read_data('sample_layering_policy')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data', 'data.layerOrder',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_passphrase_missing_required_sections(self):
        document = self._read_data('sample_passphrase')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data', 'metadata.storagePolicy',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_validation_policy_missing_required_sections(self):
        document = self._read_data('sample_validation_policy')
        properties_to_remove = tuple(self.exception_map.keys()) + (
            'data', 'data.validations', 'data.validations.0.name')
        self._test_missing_required_sections(document, properties_to_remove)

    @mock.patch.object(document_validation, 'LOG', autospec=True)
    def test_invalid_document_schema_generates_error(self, mock_log):
        document = self._read_data('sample_document')
        document['schema'] = 'foo/bar/v1'

        doc_validator = document_validation.DocumentValidation(document)
        doc_validator.validate_all()
        self.assertRegex(
            mock_log.error.mock_calls[0][1][0],
            'The provided document schema %s is invalid.' % document['schema'])

    @mock.patch.object(document_validation, 'LOG', autospec=True)
    def test_invalid_document_schema_version_generates_error(self, mock_log):
        document = self._read_data('sample_passphrase')
        document['schema'] = 'deckhand/Passphrase/v5'

        doc_validator = document_validation.DocumentValidation(document)
        doc_validator.validate_all()
        self.assertRegex(
            mock_log.error.mock_calls[0][1][0],
            'The provided document schema %s is invalid.' % document['schema'])
