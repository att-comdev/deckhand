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

import copy
import os
import testtools
import yaml

import six

from deckhand.engine import document_validation
from deckhand import errors
from deckhand.tests.unit import base as test_base


class TestDocumentValidation(test_base.DeckhandTestCase):

    def _read_data(self, file_name):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_yaml_path = os.path.abspath(os.path.join(
            dir_path, os.pardir, 'resources', file_name + '.yaml'))

        with open(test_yaml_path, 'r') as yaml_file:
            yaml_data = yaml_file.read()
        self.data = yaml.safe_load(yaml_data)

    def _corrupt_data(self, key, value=None, data=None, op='delete'):
        """Corrupt test data to check that pre-validation works.

        Corrupt data by removing a key from the document. Each key must
        correspond to a value that is a dictionary.

        :param key: The document key to be removed. The key can have the
            following formats:
                * 'data' => document.pop('data')
                * 'metadata.name' => document['metadata'].pop('name')
                * 'metadata.substitutions.0.dest' =>
                   document['metadata']['substitutions'][0].pop('dest')
        :returns: Corrupted data.
        """
        if data is None:
            data = self.data
        corrupted_data = copy.deepcopy(data)

        if '.' in key:
            _corrupted_data = corrupted_data
            nested_keys = key.split('.')
            for nested_key in nested_keys:
                if nested_key == nested_keys[-1]:
                    break
                if nested_key.isdigit():
                    _corrupted_data = _corrupted_data[int(nested_key)]
                else:
                    _corrupted_data = _corrupted_data[nested_key]
            if op == 'delete':
                _corrupted_data.pop(nested_keys[-1])
            elif op == 'replace':
                _corrupted_data[nested_keys[-1]] = value
        else:
            if op == 'delete':
                corrupted_data.pop(key)
            elif op == 'replace':
                corrupted_data[key] = value

        return corrupted_data

    def test_init_document_validation(self):
        self._read_data('sample_document')
        doc_validation = document_validation.DocumentValidation(
            self.data)
        self.assertIsInstance(doc_validation,
                              document_validation.DocumentValidation)

    def test_certificate_key_schema_missing_required_sections(self):
        self._read_data('sample_certificate_key')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'metadata.storagePolicy', 'data']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_certificate_schema_missing_required_sections(self):
        self._read_data('sample_certificate')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'metadata.storagePolicy', 'data']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_data_schema_missing_required_sections(self):
        self._read_data('sample_data_schema')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'data.$schema']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            e = self.assertRaises(
                errors.InvalidFormat, document_validation.DocumentValidation,
                invalid_data)
            self.assertIn(expected_err % missing_prop, str(e))

    def test_data_schema_missing_optional_sections(self):
        self._read_data('sample_data_schema')
        optional_missing_data = [
            self._corrupt_data('metadata.labels'),
        ]

        for missing_data in optional_missing_data:
            document_validation.DocumentValidation(missing_data)

    def test_document_schema_missing_required_sections(self):
        self._read_data('sample_document')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['schema', 'metadata', 'metadata.schema',
                                'metadata.name', 'metadata.substitutions',
                                'metadata.substitutions.0.dest',
                                'metadata.substitutions.0.dest.path',
                                'metadata.substitutions.0.src',
                                'metadata.substitutions.0.src.schema',
                                'metadata.substitutions.0.src.name',
                                'metadata.substitutions.0.src.path', 'data']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            e = self.assertRaises(
                errors.InvalidFormat, document_validation.DocumentValidation,
                invalid_data)
            self.assertIn(expected_err % missing_prop, str(e))


    def test_document_schema_missing_optional_sections(self):
        self._read_data('sample_document')
        properties_to_remove = ['metadata.substitutions.2.dest.pattern']

        for property_to_remove in properties_to_remove:
            optional_data_removed = self._corrupt_data(property_to_remove)
            document_validation.DocumentValidation(optional_data_removed)

    def test_layering_policy_schema_missing_required_sections(self):
        self._read_data('sample_layering_policy')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'data.layerOrder']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_prop):
                document_validation.DocumentValidation(invalid_data)

    def test_passphrase_missing_required_sections(self):
        self._read_data('sample_passphrase')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'metadata.storagePolicy', 'data']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_prop):
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

    def test_validation_policy_schema_missing_required_sections(self):
        self._read_data('sample_validation_policy')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        properties_to_remove = ['metadata', 'metadata.schema', 'metadata.name',
                                'data', 'data.validations',
                                'data.validations.0.name']

        for property_to_remove in properties_to_remove:
            missing_prop = property_to_remove.split('.')[-1]
            invalid_data = self._corrupt_data(property_to_remove)

            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_prop):
                document_validation.DocumentValidation(invalid_data)
