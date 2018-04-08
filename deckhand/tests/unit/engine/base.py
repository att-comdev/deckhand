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
import yaml

from deckhand.engine import layering
from deckhand.tests.unit import base as test_base
from deckhand import types


class BaseEngineTestCase(test_base.DeckhandTestCase):

    def _test_layering(self, documents, site_expected=None,
                       region_expected=None, global_expected=None,
                       validate=False, strict=True, **kwargs):
        # TODO(fmontei): Refactor all tests to work with strict=True.

        # Test layering twice: once by passing in the documents in the normal
        # order and again with the documents in reverse order for good measure,
        # to verify that the documents are being correctly sorted by their
        # substitution dependency chain.
        for documents in (documents, list(reversed(documents))):
            document_layering = layering.DocumentLayering(
                documents, validate=validate, **kwargs)

            site_docs = []
            region_docs = []
            global_docs = []

            # The layering policy is not returned as it is immutable. So all
            # docs should have a metadata.layeringDefinitionn.layer section.
            rendered_documents = document_layering.render()
            for doc in rendered_documents:
                # No need to validate the LayeringPolicy: it remains unchanged.
                if doc['schema'].startswith(types.LAYERING_POLICY_SCHEMA):
                    continue
                layer = doc['metadata']['layeringDefinition']['layer']
                if layer == 'site':
                    site_docs.append(doc.get('data'))
                if layer == 'region':
                    region_docs.append(doc.get('data'))
                if layer == 'global':
                    global_docs.append(doc.get('data'))

            if site_expected is not None:
                if not isinstance(site_expected, list):
                    site_expected = [site_expected]

                if strict:
                    self.assertEqual(len(site_expected), len(site_docs))

                for expected in site_expected:
                    self.assertIn(expected, site_docs)
                    idx = site_docs.index(expected)
                    self.assertEqual(
                        expected, site_docs[idx],
                        'Actual site data does not match expected.')
                    site_docs.remove(expected)
            else:
                self.assertEmpty(site_docs)

            if region_expected is not None:
                if not isinstance(region_expected, list):
                    region_expected = [region_expected]

                if strict:
                    self.assertEqual(len(region_expected), len(region_docs))

                for expected in region_expected:
                    self.assertIn(expected, region_docs)
                    idx = region_docs.index(expected)
                    self.assertEqual(
                        expected, region_docs[idx],
                        'Actual region data does not match expected.')
                    region_docs.remove(expected)
            else:
                self.assertEmpty(region_docs)

            if global_expected is not None:
                if not isinstance(global_expected, list):
                    global_expected = [global_expected]

                if strict:
                    self.assertEqual(len(global_expected), len(global_docs))

                for expected in global_expected:
                    self.assertIn(expected, global_docs)
                    idx = global_docs.index(expected)
                    self.assertEqual(
                        expected, global_docs[idx],
                        'Actual global data does not match expected.')
                    global_docs.remove(expected)
            else:
                self.assertEmpty(global_docs)

    def _read_data(self, file_name):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_yaml_path = os.path.abspath(os.path.join(
            dir_path, os.pardir, 'resources', file_name + '.yaml'))

        with open(test_yaml_path, 'r') as yaml_file:
            yaml_data = yaml_file.read()
        return yaml.safe_load(yaml_data)

    def _corrupt_data(self, data, key, value=None, op='delete'):
        """Corrupt test data to check that pre-validation works.

        Corrupt data by removing a key from the document (if ``op`` is delete)
        or by replacing the value corresponding to the key with ``value`` (if
        ``op`` is replace).

        :param key: The document key to be removed. The key can have the
            following formats:
                * 'data' => document.pop('data')
                * 'metadata.name' => document['metadata'].pop('name')
                * 'metadata.substitutions.0.dest' =>
                   document['metadata']['substitutions'][0].pop('dest')
        :type key: string
        :param value: The new value that corresponds to the (nested) document
            key (only used if ``op`` is 'replace').
        :type value: type string
        :param data: The data to "corrupt".
        :type data: dict
        :param op: Controls whether data is deleted (if "delete") or is
            replaced with ``value`` (if "replace").
        :type op: string
        :returns: Corrupted data.
        """
        if op not in ('delete', 'replace'):
            raise ValueError("The ``op`` argument must either be 'delete' or "
                             "'replace'.")
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
