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

import testtools

from deckhand.engine import layering
from deckhand import errors


class TestDocumentLayering(testtools.TestCase):

    FAKE_YAML_DATA_2_LAYERS = """
---
schema: deckhand/LayeringPolicy/v1
metadata:
  schema: metadata/Control/v1
  name: layering-policy
data:
  layerOrder:
    - global
    - site
---
schema: example/Kind/v1
metadata:
  schema: metadata/Document/v1
  name: global-1234
  labels:
    key1: value1
  layeringDefinition:
    abstract: true
    layer: global
data:
  a:
    x: 1
    y: 2
  c: 9
---
schema: example/Kind/v1
metadata:
  schema: metadata/Document/v1
  name: site-1234
  layeringDefinition:
    layer: site
    parentSelector:
      key1: value1
    actions:
      - method: {method}
        path: {path}
data:
  a:
    x: 7
    z: 3
  b: 4"""

    FAKE_YAML_DATA_3_LAYERS = """
---
schema: deckhand/LayeringPolicy/v1
metadata:
  schema: metadata/Control/v1
  name: layering-policy
data:
  layerOrder:
    - global
    - region
    - site
---
schema: example/Kind/v1
metadata:
  schema: metadata/Document/v1
  name: global-1234
  labels:
    key1: value1
  layeringDefinition:
    abstract: true
    layer: global
data:
  a:
    x: 1
    y: 2
---
schema: example/Kind/v1
metadata:
  schema: metadata/Document/v1
  name: region-1234
  labels:
    key1: value1
  layeringDefinition:
    abstract: true
    layer: region
    parentSelector:
      key1: value1
    actions:
      - method: replace
        path: .a
data:
  a:
    z: 3
---
schema: example/Kind/v1
metadata:
  schema: metadata/Document/v1
  name: site-1234
  layeringDefinition:
    layer: site
    parentSelector:
      key1: value1
    actions:
      - method: merge
        path: .
data:
  b: 4"""

    def _read_data(self, filename):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_yaml_path = os.path.abspath(os.path.join(
            dir_path, os.pardir, 'resources', filename))

        with open(test_yaml_path, 'r') as yaml_file:
            yaml_data = yaml_file.read()
        return self._parse_data(yaml_data)

    def _parse_data(self, yaml_data):
        return [d for d in yaml.safe_load_all(yaml_data)]

    def _test_layering(self, expected, documents):
        document_layering = layering.DocumentLayering(documents)
        rendered_data = document_layering.render()
        self.assertEqual(expected, rendered_data)


class TestDocumentLayering2Layers(TestDocumentLayering):

    def test_layering_method_delete(self):
        expected = [{}, {'b': 4}]

        for idx, path in enumerate(['.', '.a']):
            documents = self._parse_data(self.FAKE_YAML_DATA_2_LAYERS.format(
                method='delete', path=path))
            self._test_layering(expected[idx], documents)

    def test_layering_method_merge(self):
        expected = [
            {'a': {'x': 7, 'y': 2, 'z': 3}, 'b': 4, 'c': 9},
            {'a': {'x': 7, 'y': 2, 'z': 3}, 'b': 4},
            # .b doesn't exist in the global layer so nothing happens.
            {'a': {'x': 7, 'z': 3}, 'b': 4},
            # .c data is copied from global layer.
            {'a': {'x': 7, 'z': 3}, 'b': 4, 'c': 9}
        ]

        for idx, path in enumerate(['.', '.a', '.b', '.c']):
            documents = self._parse_data(self.FAKE_YAML_DATA_2_LAYERS.format(
                method='merge', path=path))
            self._test_layering(expected[idx], documents)

    # def test_layering_method_replace(self):
    #     expected = [
    #         {'a': {'x': 7, 'z': 3}, 'b': 4}
    #     ]

    #     for idx, path in enumerate(['.']):
    #         documents = self._parse_data(self.FAKE_YAML_DATA_2_LAYERS.format(
    #             method='replace', path=path))
    #         self._test_layering(expected[idx], documents)


class TestDocumentLayering3Layers(TestDocumentLayering):

    def test_layering_default_scenario(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_delete_everything(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'delete'}
        ]

        expected = {}
        self._test_layering(expected, documents)

    def test_layering_delete_path_a(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'delete'}
        ]

        expected = {'b': 4}
        self._test_layering(expected, documents)

    def test_layering_merge_and_replace(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'replace'}
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'y': 2, 'x': 1}, 'b': {'w': 4, 'v': 3}}
        self._test_layering(expected, documents)

    def test_layering_double_merge(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[2]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'merge'}
        ]
        documents[1]['data'] = {
            'c': {'e': 55}
        }

        expected = {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': {'e': 55}}
        self._test_layering(expected, documents)

    def test_layering_double_merge_2(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'merge'}
        ]
        documents[2]['data'] = {
            'a': {'e': 55}
        }

        expected = {'a': {'x': 1, 'y': 2, 'e': 55}, 'b': 4}
        self._test_layering(expected, documents)


class TestDocumentLayering3LayersScenario(TestDocumentLayering):

    def test_layering_multiple_delete(self):
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'delete'},
            {'path': '.', 'method': 'delete'}
        ]

        expected = {}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_1(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': 4}
        """
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'replace'},
            {'path': '.a', 'method': 'replace'},
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_2(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        """
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'replace'},
            {'path': '.b', 'method': 'replace'},
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_3(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        """
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'replace'},
            {'path': '.b', 'method': 'replace'},
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_4(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        """
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'replace'},
            {'path': '.b', 'method': 'replace'},
            {'path': '.c', 'method': 'replace'}
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        self._test_layering(expected, documents)

    def test_layering_multiple_delete_replace(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Delete (.): {}
        Replace (.a): {'a': {'x': 1, 'y': 2}}
        Delete (.a): {}
        Replace (.b): {'b': {'v': 3, 'w': 4}}
        """
        documents = self._parse_data(self.FAKE_YAML_DATA_3_LAYERS)
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'delete'},
            {'path': '.a', 'method': 'replace'},
            {'path': '.a', 'method': 'delete'},
            {'path': '.b', 'method': 'replace'}
        ]

        expected = {'b': {'v': 3, 'w': 4}}
        self._test_layering(expected, documents)
