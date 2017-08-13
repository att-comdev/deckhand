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

from deckhand.engine import document_validation
from deckhand import errors
from deckhand.tests import test_utils
from deckhand.tests.unit.engine import base as engine_test_base


class TestDocumentValidationNegative(
        engine_test_base.TestDocumentValidationBase):
    """Negative testing suite for document validation."""

    # NOTE(fmontei): The "data" key is omitted from `BASIC_ATTRS` since
    # Tombstone documents do not have it, so the base schema used for universal
    # validation does not require it.
    BASIC_ATTRS = (
        'schema', 'metadata', 'metadata.schema', 'metadata.name')
    SCHEMA_ERR = ("The provided YAML failed schema validation. "
                  "Details: '%s' is a required property.")
    SCHEMA_ERR_ALT = ("The provided %s YAML failed schema validation. "
                      "Details: '%s' is a required property.")

    def _test_missing_required_sections(self, doc_data, properties_to_remove):
        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(doc_data, property_to_remove)

            if property_to_remove in self.BASIC_ATTRS:
                expected_err = self.SCHEMA_ERR % missing_prop
            else:
                expected_err = self.SCHEMA_ERR_ALT % (
                    doc_data['schema'], missing_prop)

            # NOTE(fmontei): '$' must be escaped for regex to pass.
            expected_err = expected_err.replace('$', '\$')

            with self.assertRaisesRegex(errors.InvalidDocumentFormat,
                                        expected_err):
                document_validation.DocumentValidation(
                    invalid_data).validate_all()

    @test_utils.file_data('../resources/sample_certificate_key.yaml')
    def test_certificate_key_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + ('metadata.storagePolicy',)
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_certificate.yaml')
    def test_certificate_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + ('metadata.storagePolicy',)
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_data_schema.yaml')
    def test_data_schema_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + ('data.$schema',)
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_document.yaml')
    def test_document_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + (
            'metadata.layeringDefinition',
            'metadata.layeringDefinition.abstract',
            'metadata.layeringDefinition.layer',
            'metadata.layeringDefinition.actions.0.method',
            'metadata.layeringDefinition.actions.0.path',
            'metadata.substitutions.0.dest',
            'metadata.substitutions.0.dest.path',
            'metadata.substitutions.0.src',
            'metadata.substitutions.0.src.schema',
            'metadata.substitutions.0.src.name',
            'metadata.substitutions.0.src.path')
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_document.yaml')
    def test_document_invalid_layering_definition_action(self, doc_data):
        wrong_data = self._corrupt_data(
            doc_data, 'metadata.layeringDefinition.actions.0.action',
            'invalid', op='replace')
        error_re = ("Additional properties are not allowed \('action' was "
                    "unexpected\).")

        doc_validation = document_validation.DocumentValidation(wrong_data)
        self.assertRaisesRegex(errors.InvalidDocumentFormat, error_re,
                               doc_validation.validate_all)

    @test_utils.file_data('../resources/sample_layering_policy.yaml')
    def test_layering_policy_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + ('data.layerOrder',)
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_passphrase.yaml')
    def test_passphrase_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + ('metadata.storagePolicy',)
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_passphrase.yaml')
    def test_passphrase_with_incorrect_storage_policy(self, doc_data):
        error_re = (
            "The provided deckhand/Passphrase/v1.0 YAML failed schema "
            "validation. Details: 'cleartext' does not match "
            "'\^\(encrypted\)\$'")
        wrong_data = self._corrupt_data(
            doc_data, 'metadata.storagePolicy', 'cleartext', op='replace')

        doc_validation = document_validation.DocumentValidation(wrong_data)
        self.assertRaisesRegex(errors.InvalidDocumentFormat, error_re,
                              doc_validation.validate_all)

    @test_utils.file_data('../resources/sample_validation_policy.yaml')
    def test_validation_policy_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS + (
            'data.validations', 'data.validations.0.name')
        self._test_missing_required_sections(doc_data, properties_to_remove)

    @test_utils.file_data('../resources/sample_tombstone_document.yaml')
    def test_tombstone_document_missing_required_sections(self, doc_data):
        properties_to_remove = self.BASIC_ATTRS
        self._test_missing_required_sections(doc_data, properties_to_remove)
