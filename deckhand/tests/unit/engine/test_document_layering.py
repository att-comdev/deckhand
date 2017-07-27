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
import json
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
    {actions}
data:
  a:
    x: 7
    z: 3
  b: 4"""

    FAKE_YAML_DATA_3_LAYERS = """[
        {
            "data": {
                "layerOrder": ["global", "region", "site"]
            },
            "metadata": {
                "name": "layering-policy",
                "schema": "metadata/Control/v1"
            },
            "schema": "deckhand/LayeringPolicy/v1"
        },
        {
            %(_GLOBAL_DATA_)s,
            "metadata": {
                "labels": {"key1": "value1"},
                "layeringDefinition": {"abstract": true, "layer": "global"},
                "name": "global-1234",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_REGION_DATA_)s,
            "metadata": {
                "labels": {"key1": "value1"},
                "layeringDefinition": {
                    "abstract": true,
                    %(_REGION_ACTIONS_)s,
                    "layer": "region",
                    "parentSelector": {"key1": "value1"}
                },
                "name": "region-1234",
                "path": ".a",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_SITE_DATA_)s,
            "metadata": {
                "layeringDefinition": {
                    %(_SITE_ACTIONS_)s,
                    "layer": "site",
                    "parentSelector": {"key1": "value1"}
                },
                "name": "site-1234",
                "path": ".a",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        }
    ]"""

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

    def _format_actions(self, count, *args):
        actions = """
    actions:
"""
        action_list = ""
        for _ in range(count):
            action = """
      - method: %s
        path: %s
"""
            action_list = action_list + action

        actions = actions + action_list
        return actions % args

    def _format_data(self, base_data, new_dict=None, **kwargs):
        if not new_dict:
            new_dict = {}

        for key, val in new_dict.items():
            new_val = json.dumps(val)[1:-1]
            new_dict[key] = new_val

        updated_data = copy.deepcopy(base_data)
        updated_data = updated_data % new_dict
        updated_data = json.loads(updated_data)

        return updated_data


class TestDocumentLayering2Layers(TestDocumentLayering):

    def test_layering_method_delete(self):
        expected = [{}, {'b': 4}]

        for idx, path in enumerate(['.', '.a']):
            actions = self._format_actions(1, 'delete', path)
            documents = self._parse_data(self.FAKE_YAML_DATA_2_LAYERS.format(
                actions=actions))
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
            actions = self._format_actions(1, 'merge', path)
            documents = self._parse_data(self.FAKE_YAML_DATA_2_LAYERS.format(
                actions=actions))
            self._test_layering(expected[idx], documents)

    def test_layering_method_replace(self):
        expected = [
            {'a': {'y': 2, 'x': 1}, 'c': 9},
            {'a': {'y': 2, 'x': 1}, 'b': 4},
            # '.b' doesn't exist in parent so do nothing.
            {'a': {'z': 3, 'x': 7}, 'b': 4},
            {'a': {'z': 3, 'x': 7}, 'b': 4, 'c': 9},
        ]

        for idx, path in enumerate(['.', '.a', '.b', '.c']):
            actions = self._format_actions(1, 'replace', path)
            documents = self._parse_data(self.FAKE_YAML_DATA_2_LAYERS.format(
                actions=actions))
            self._test_layering(expected[idx], documents)


class TestDocumentLayering3Layers(TestDocumentLayering):

    def test_layering_default_scenario(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{"method": "replace", "path": ".a"}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_delete_everything(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_": {
                "data": {"a": {"x": 1, "y": 2}, "b": {"v": 3, "w": 4}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{"path": ".", "method": "delete"}]},
            "_SITE_ACTIONS_": {"actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {}
        self._test_layering(expected, documents)

    def test_layering_delete_path_a(self):
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'delete'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'b': 4}
        self._test_layering(expected, documents)

    def test_layering_merge_and_replace(self):
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_": {"data": {'a': {'z': 5}}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'y': 2, 'x': 1}, 'b': {'w': 4, 'v': 3}}
        self._test_layering(expected, documents)

    def test_layering_double_merge(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"c": {"e": 55}}},
            "_REGION_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_SITE_DATA_": {"data": {"a": {"z": 5}}},
            "_REGION_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_ACTIONS_": {"actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'x': 1, 'y': 2, 'z': 5},
                    'b': {'v': 3, 'w': 4}, 'c': {'e': 55}}
        self._test_layering(expected, documents)

    def test_layering_double_merge_2(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {'a': {'e': 55}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'merge'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'x': 1, 'y': 2, 'e': 55}, 'b': 4}
        self._test_layering(expected, documents)


class TestDocumentLayering3LayersScenario(TestDocumentLayering):

    def test_layering_multiple_delete(self):
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.', 'method': 'delete'},
                            {'path': '.', 'method': 'delete'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_1(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': 4}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.a', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_2(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_3(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4},
                         'c': [123]}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        self._test_layering(expected, documents)

    def test_layering_multiple_replace_4(self):
        """Scenario:
        
        Initially: {'b': 4}
        Merge: {'a': {'z': 5}, 'b': 4}
        Replace:  {'a': {'x': 1, 'y': 2}, 'b': 4}
        Replace: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4},
                         'c': [123]}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'},
                            {'path': '.c', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
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
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.', 'method': 'delete'},
                            {'path': '.a', 'method': 'replace'},
                            {'path': '.a', 'method': 'delete'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        expected = {'b': {'v': 3, 'w': 4}}
        self._test_layering(expected, documents)
