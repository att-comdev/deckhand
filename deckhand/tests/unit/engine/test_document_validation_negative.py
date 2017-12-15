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
from deckhand import types


class TestDocumentValidationNegative(
        engine_test_base.TestDocumentValidationBase):
    """Negative testing suite for document validation."""

    # The 'data' key is mandatory but not critical if excluded.
    CRITICAL_ATTRS = (
        'schema', 'metadata', 'metadata.schema', 'metadata.name')
    SCHEMA_ERR = "'%s' is a required property"

    def setUp(self):
        super(TestDocumentValidationNegative, self).setUp()
        self.dataschema_factory = factories.DataSchemaFactory()

    def _test_missing_required_sections(self, document, properties_to_remove):
        for idx, property_to_remove in enumerate(properties_to_remove):
            critical = property_to_remove in self.CRITICAL_ATTRS

            dataschema = self.dataschema_factory.gen_test(
                document['schema'], {})

            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(document, property_to_remove)
            expected_err = self.SCHEMA_ERR % missing_prop

            # Ensure that a dataschema document exists for the random
            # sample document schema via mocking.
            with mock.patch('deckhand.db.sqlalchemy.api.document_get_all',
                    return_value=[dataschema], autospec=True):
                doc_validator = document_validation.DocumentValidation(
                    invalid_data)
            if critical:
                self.assertRaisesRegexp(
                    errors.InvalidDocumentFormat, expected_err,
                    doc_validator.validate_all)
            else:
                validations = doc_validator.validate_all()
                self.assertEqual(1, len(validations))
                self.assertEqual('failure', validations[0]['status'])
                self.assertEqual({'version': '1.0', 'name': 'deckhand'},
                                 validations[0]['validator'])
                self.assertEqual(types.DECKHAND_SCHEMA_VALIDATION,
                                 validations[0]['name'])
                self.assertEqual(1, len(validations[0]['errors']))
                self.assertEqual(document['metadata']['name'],
                                 validations[0]['errors'][0]['name'])
                self.assertEqual(document['schema'],
                                 validations[0]['errors'][0]['schema'])
                self.assertEqual(expected_err,
                                 validations[0]['errors'][0]['message'])

    def test_certificate_key_missing_required_sections(self):
        document = self._read_data('sample_certificate_key')
        properties_to_remove = self.CRITICAL_ATTRS + (
            'data', 'metadata.storagePolicy',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_certificate_missing_required_sections(self):
        document = self._read_data('sample_certificate')
        properties_to_remove = self.CRITICAL_ATTRS + (
            'data', 'metadata.storagePolicy',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_data_schema_missing_required_sections(self):
        document = self._read_data('sample_data_schema')
        properties_to_remove = self.CRITICAL_ATTRS + ('data', 'data.$schema',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_document_missing_required_sections(self):
        document = self._read_data('sample_document')
        properties_to_remove = self.CRITICAL_ATTRS + (
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
        corrupted_data = self._corrupt_data(
            document, 'metadata.layeringDefinition.actions.0.method',
            'invalid', op='replace')
        expected_err = "'invalid' is not one of ['replace', 'delete', 'merge']"

        # Ensure that a dataschema document exists for the random document
        # schema via mocking.
        dataschema = self.dataschema_factory.gen_test(document['schema'], {})
        with mock.patch('deckhand.db.sqlalchemy.api.document_get_all',
                        return_value=[dataschema], autospec=True):
            doc_validator = document_validation.DocumentValidation(
                corrupted_data)
        validations = doc_validator.validate_all()
        self.assertEqual(1, len(validations))
        self.assertEqual('failure', validations[0]['status'])
        self.assertEqual({'version': '1.0', 'name': 'deckhand'},
                         validations[0]['validator'])
        self.assertEqual(types.DECKHAND_SCHEMA_VALIDATION,
                         validations[0]['name'])
        self.assertEqual(1, len(validations[0]['errors']))
        self.assertEqual(document['metadata']['name'],
                         validations[0]['errors'][0]['name'])
        self.assertEqual(document['schema'],
                         validations[0]['errors'][0]['schema'])
        self.assertEqual(expected_err,
                         validations[0]['errors'][0]['message'])

    def test_layering_policy_missing_required_sections(self):
        document = self._read_data('sample_layering_policy')
        properties_to_remove = self.CRITICAL_ATTRS + (
            'data', 'data.layerOrder',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_passphrase_missing_required_sections(self):
        document = self._read_data('sample_passphrase')
        properties_to_remove = self.CRITICAL_ATTRS + (
            'data', 'metadata.storagePolicy',)
        self._test_missing_required_sections(document, properties_to_remove)

    def test_validation_policy_missing_required_sections(self):
        document = self._read_data('sample_validation_policy')
        properties_to_remove = self.CRITICAL_ATTRS + (
            'data', 'data.validations', 'data.validations.0.name')
        self._test_missing_required_sections(document, properties_to_remove)
