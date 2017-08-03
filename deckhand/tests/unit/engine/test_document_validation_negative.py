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

import six

from deckhand.engine import document_validation
from deckhand import errors
from deckhand.tests.unit.engine import test_document_validation


class TestDocumentValidationNegative(
        test_document_validation.TestDocumentValidationBase):
    """Negative testing suite for document validation."""

    def test_certificate_key_missing_required_sections(self):
        self._read_data('sample_certificate_key')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 4) + (expected_err_alt,)

        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'metadata.storagePolicy']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_errors[idx] % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_certificate_missing_required_sections(self):
        self._read_data('sample_certificate')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 4) + (expected_err_alt,)

        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'metadata.storagePolicy']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_errors[idx] % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_data_schema_missing_required_sections(self):
        self._read_data('sample_data_schema')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 4) + (expected_err_alt,)

        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'data.$schema']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            e = self.assertRaises(
                errors.InvalidFormat, document_validation.DocumentValidation,
                invalid_data)
            self.assertIn(expected_errors[idx] % missing_prop, str(e))

    def test_document_missing_required_sections(self):
        self._read_data('sample_document')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 5) + ((expected_err_alt,) * 7)

        properties_to_remove = ['schema', 'metadata', 'data',
                                'metadata.schema', 'metadata.name',
                                'metadata.substitutions',
                                'metadata.substitutions.0.dest',
                                'metadata.substitutions.0.dest.path',
                                'metadata.substitutions.0.src',
                                'metadata.substitutions.0.src.schema',
                                'metadata.substitutions.0.src.name',
                                'metadata.substitutions.0.src.path']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_errors[idx] % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_layering_policy_missing_required_sections(self):
        self._read_data('sample_layering_policy')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 4) + (expected_err_alt,)

        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'data.layerOrder']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_errors[idx] % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_passphrase_missing_required_sections(self):
        self._read_data('sample_passphrase')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 4) + (expected_err_alt,)

        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'metadata.storagePolicy']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_errors[idx] % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_passphrase_with_incorrect_storage_policy(self):
        self._read_data('sample_passphrase')
        expected_err = ("The provided YAML file is invalid. Exception: "
                        "'cleartext' does not match '^(encrypted)$'.")
        wrong_data = self._corrupt_data('metadata.storagePolicy', 'cleartext',
                                        op='replace')

        e = self.assertRaises(
            errors.InvalidFormat, document_validation.DocumentValidation,
            wrong_data)
        self.assertIn(expected_err, str(e))

    def test_validation_policy_missing_required_sections(self):
        self._read_data('sample_validation_policy')
        expected_err = ("The provided YAML file failed basic validation. "
                       "Exception: '%s' is a required property.")
        expected_err_alt = ("The provided YAML file is invalid. Exception: "
                            "'%s' is a required property.")
        expected_errors = ((expected_err,) * 4) + ((expected_err_alt,) * 2)

        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'data.validations',
                                'data.validations.0.name']

        for idx, property_to_remove in enumerate(properties_to_remove):
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_errors[idx] % missing_prop):
                document_validation.DocumentValidation(invalid_data)
