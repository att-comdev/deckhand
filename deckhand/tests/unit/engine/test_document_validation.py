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

    def _corrupt_data(self, key, data=None):
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
            _corrupted_data.pop(nested_keys[-1])
        else:
            corrupted_data.pop(key)

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
        invalid_data = [
            (self._corrupt_data('schema'), 'schema'),
            (self._corrupt_data('metadata'), 'metadata'),
            (self._corrupt_data('metadata.schema'), 'schema'),
            (self._corrupt_data('metadata.name'), 'name'),
            (self._corrupt_data('metadata.storagePolicy'), 'storagePolicy'),
            (self._corrupt_data('data'), 'data')
        ]

        for invalid_entry, missing_key in invalid_data:
            print invalid_entry
            print "KEY", missing_key, "\n"
            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_key):
                document_validation.DocumentValidation(invalid_entry)

    def test_data_schema_missing_required_sections(self):
        self._read_data('sample_data_schema')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        invalid_data = [
            (self._corrupt_data('schema'), 'schema'),
            (self._corrupt_data('metadata'), 'metadata'),
            (self._corrupt_data('metadata.schema'), 'schema'),
            (self._corrupt_data('metadata.name'), 'name'),
            (self._corrupt_data('data'), 'data'),
            (self._corrupt_data('data.$schema'), '$schema')
        ]

        for invalid_entry, missing_key in invalid_data:
            e = self.assertRaises(
                errors.InvalidFormat,  document_validation.DocumentValidation,
                invalid_entry)
            self.assertIn(expected_err % missing_key, str(e))

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
        invalid_data = [
            (self._corrupt_data('schema'), 'schema'),
            (self._corrupt_data('metadata'), 'metadata'),
            (self._corrupt_data('metadata.schema'), 'schema'),
            (self._corrupt_data('metadata.name'), 'name'),
            (self._corrupt_data('metadata.substitutions'), 'substitutions'),
            (self._corrupt_data('metadata.substitutions.0.dest'), 'dest'),
            (self._corrupt_data('metadata.substitutions.0.dest.path'), 'path'),
            (self._corrupt_data('metadata.substitutions.0.src'), 'src'),
            (self._corrupt_data('metadata.substitutions.0.src.schema'),
             'schema'),
            (self._corrupt_data('metadata.substitutions.0.src.name'), 'name'),
            (self._corrupt_data('metadata.substitutions.0.src.path'), 'path'),
            (self._corrupt_data('data'), 'data'),
        ]

        for invalid_entry, missing_key in invalid_data:
            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_key):
                document_validation.DocumentValidation(invalid_entry)

    def test_document_schema_missing_optional_sections(self):
        self._read_data('sample_document')
        optional_missing_data = [
            self._corrupt_data('metadata.substitutions.2.dest.pattern')
        ]

        for missing_data in optional_missing_data:
            document_validation.DocumentValidation(missing_data)

    def test_layering_policy_schema_missing_required_sections(self):
        self._read_data('sample_layering_policy')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        invalid_data = [
            (self._corrupt_data('schema'), 'schema'),
            (self._corrupt_data('metadata'), 'metadata'),
            (self._corrupt_data('metadata.schema'), 'schema'),
            (self._corrupt_data('metadata.name'), 'name'),
            (self._corrupt_data('data'), 'data'),
            (self._corrupt_data('data.layerOrder'), 'layerOrder'),
        ]

        for invalid_entry, missing_key in invalid_data:
            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_key):
                document_validation.DocumentValidation(invalid_entry)

    def test_validation_policy_schema_missing_required_sections(self):
        self._read_data('sample_validation_policy')
        expected_err = ("The provided YAML file is invalid. Exception: '%s' is"
                        " a required property.")
        invalid_data = [
            (self._corrupt_data('schema'), 'schema'),
            (self._corrupt_data('metadata'), 'metadata'),
            (self._corrupt_data('metadata.schema'), 'schema'),
            (self._corrupt_data('metadata.name'), 'name'),
            (self._corrupt_data('data'), 'data'),
            (self._corrupt_data('data.validations'), 'validations'),
            (self._corrupt_data('data.validations.0.name'), 'name'),
        ]

        for invalid_entry, missing_key in invalid_data:
            with six.assertRaisesRegex(self, errors.InvalidFormat,
                                       expected_err % missing_key):
                document_validation.DocumentValidation(invalid_entry)
