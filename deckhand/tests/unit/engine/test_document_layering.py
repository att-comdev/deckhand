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

    # These templates are used across the tests below. To use, they must be
    # first passed to ``_format_data`` below with the correct mapping (for
    # string substitution). This allows for code reusability but also a degree
    # of control over dynamic data generation.
    FAKE_YAML_DATA_2_LAYERS = """[
        {
            "data": {
                "layerOrder": ["global", "site"]
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
                   "layeringDefinition": {
                        "abstract": %(_REGION_ABSTRACT_)s,
                        "layer": "global"
                    },
                    "name": "global-1234",
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
            "schema": "metadata/Document/v1"
        },
        "schema": "example/Kind/v1"}
    ]"""

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
                "labels": {"global": "global1"},
                "layeringDefinition": {
                    "abstract": %(_GLOBAL_ABSTRACT_)s,
                    "layer": "global"
                },
                "name": "global-1234",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_REGION_DATA_)s,
            "metadata": {
                "labels": {"region": "region1"},
                "layeringDefinition": {
                    "abstract": %(_REGION_ABSTRACT_)s,
                    %(_REGION_ACTIONS_)s,
                    "layer": "region",
                    "parentSelector": {"global": "global1"}
                },
                "name": "region-1234",
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
                    "parentSelector": {"region": "region1"}
                },
                "name": "site-1234",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        }
    ]"""

    FAKE_YAML_DATA_2_LAYERS_2_SITES = """[
        {
            "data": {
                "layerOrder": ["global", "site"]
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
                "layeringDefinition": {
                    "abstract": %(_GLOBAL_ABSTRACT_)s,
                    "layer": "global"
                },
                "name": "global-1234",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_SITE_DATA_ONE_)s,
            "metadata": {
                "layeringDefinition": {
                    %(_SITE_ACTIONS_ONE_)s,
                    "layer": "site",
                    "parentSelector": {"key1": "value1"}
                },
                "name": "site-1234",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_SITE_DATA_TWO_)s,
            "metadata": {
                "layeringDefinition": {
                    %(_SITE_ACTIONS_TWO_)s,
                    "layer": "site",
                    "parentSelector": {"key1": "value1"}
                },
                "name": "site-1235",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        }
    ]"""

    FAKE_YAML_DATA_3_LAYERS_2_REGIONS_2_SITES = """[
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
                "labels": {"global": "global1"},
                "layeringDefinition": {
                    "abstract": %(_GLOBAL_ABSTRACT_)s,
                    "layer": "global"
                },
                "name": "global-1",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_REGION_DATA_ONE_)s,
            "metadata": {
                "labels": {"region": "region1"},
                "layeringDefinition": {
                    "abstract": %(_REGION_ABSTRACT_)s,
                    %(_REGION_ACTIONS_ONE_)s,
                    "layer": "region",
                    "parentSelector": {"global": "global1"}
                },
                "name": "region-1",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_REGION_DATA_TWO_)s,
            "metadata": {
                "labels": {"region": "region2"},
                "layeringDefinition": {
                    "abstract": %(_REGION_ABSTRACT_)s,
                    %(_REGION_ACTIONS_TWO_)s,
                    "layer": "region",
                    "parentSelector": {"global": "global1"}
                },
                "name": "region-2",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_SITE_DATA_ONE_)s,
            "metadata": {
                "layeringDefinition": {
                    %(_SITE_ACTIONS_ONE_)s,
                    "layer": "site",
                    "parentSelector": {"region": "region1"}
                },
                "name": "site-1",
                "schema": "metadata/Document/v1"
            },
            "schema": "example/Kind/v1"
        },
        {
            %(_SITE_DATA_TWO_)s,
            "metadata": {
                "layeringDefinition": {
                    %(_SITE_ACTIONS_TWO_)s,
                    "layer": "site",
                    "parentSelector": {"region": "region2"}
                },
                "name": "site-2",
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
        return [d for d in yaml.safe_load_all(yaml_data)]

    def _test_layering(self, documents, site_expected=None,
                       region_expected=None, global_expected=None,
                       exception_expected=None):
        document_layering = layering.DocumentLayering(documents)

        if all([site_expected, region_expected, global_expected,
                exception_expected]):
            raise ValueError(
                '(site_expected|region_expected|global_expected) and '
                '(exception_expected) are mutually exclusive.')

        if exception_expected:
            self.assertRaises(exception_expected, document_layering.render)
            return

        site_docs = []
        region_docs = []
        global_docs = []

        # The layering policy is not returned as it is immutable. So all docs
        # should have a metadata.layeringDefinitionn.layer section.
        rendered_documents = document_layering.render()
        for doc in rendered_documents:
            layer = doc['metadata']['layeringDefinition']['layer']
            if layer == 'site':
                site_docs.append(doc)
            if layer == 'region':
                region_docs.append(doc)
            if layer == 'global':
                global_docs.append(doc)

        if site_expected:
            if not isinstance(site_expected, list):
                site_expected = [site_expected]

            for idx, expected in enumerate(site_expected):
                self.assertEqual(expected, site_docs[idx].get('data'))
        if region_expected:
            if not isinstance(region_expected, list):
                region_expected = [region_expected]

            for idx, expected in enumerate(region_expected):
                self.assertEqual(expected, region_docs[idx].get('data'))
        if global_expected:
            if not isinstance(global_expected, list):
                global_expected = [global_expected]

            for idx, expected in enumerate(global_expected):
                self.assertEqual(expected, global_docs[idx].get('data'))

    def _format_data(self, dict_as_string, mapping=None,
                     region_abstract=True, global_abstract=True):
        """Format ``dict_as_string`` by mapping dummy keys using ``mapping``.

        :param dict_as_string: JSON-serialized dictionary.
        :param mapping: Mapping used to substitute dummy variables with proper
            data.
        """
        if not mapping:
            mapping = {}

        mapping['_REGION_ABSTRACT_'] = str(region_abstract).lower()
        mapping['_GLOBAL_ABSTRACT_'] = str(global_abstract).lower()

        for key, val in mapping.items():
            new_val = json.dumps(val)[1:-1]
            mapping[key] = new_val

        updated_data = copy.deepcopy(dict_as_string)

        # NOTE: Auto-populate the missing keys if they aren't provided with
        # '"actions": {}' or '"data": {}' depending on whether the missing key
        # contains ACTIONS or DATA in it, respectively. Used for negative
        # testing.
        while True:
            try:
                updated_data = updated_data % mapping
                break
            except KeyError as e:
                missing_key = e.args[0]
                key_type = missing_key.split('_')[-2].lower()
                mapping[missing_key] = '"%s": %s' % (key_type, {})

        updated_data = json.loads(updated_data)

        return updated_data


class TestDocumentLayering2Layers(TestDocumentLayering):

    def test_layering_default_scenario(self):
        # Default scenario mentioned in design document for 2 layers (region
        # data is removed).
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs)
        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_method_delete(self):
        site_expected = [{}, {'c': 9}, {"a": {"x": 1, "y": 2}}]

        for idx, path in enumerate(['.', '.a', '.c']):
            kwargs = {
                "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
                "_SITE_DATA_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
                "_SITE_ACTIONS_": {
                    "actions": [{"method": "delete", "path": path}]}
            }
            documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs)
            self._test_layering(documents, site_expected[idx])

    def test_layering_method_merge(self):
        site_expected = [
            {'a': {'x': 7, 'y': 2, 'z': 3}, 'b': 4, 'c': 9},
            {'a': {'x': 7, 'y': 2, 'z': 3}, 'c': 9},
            {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': 9}
        ]

        for idx, path in enumerate(['.', '.a', '.b']):
            kwargs = {
                "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
                "_SITE_DATA_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
                "_SITE_ACTIONS_": {
                    "actions": [{"method": "merge", "path": path}]}
            }
            documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs)
            self._test_layering(documents, site_expected[idx])

    def test_layering_method_replace(self):
        site_expected = [
            {'a': {'x': 7, 'z': 3}, 'b': 4},
            {'a': {'x': 7, 'z': 3}, 'c': 9},
            {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': 9}
        ]

        for idx, path in enumerate(['.', '.a', '.b']):
            kwargs = {
                "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
                "_SITE_DATA_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
                "_SITE_ACTIONS_": {
                    "actions": [{"method": "replace", "path": path}]}
            }
            documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs)
            self._test_layering(documents, site_expected[idx])


class TestDocumentLayering2LayersAbstractConcrete(TestDocumentLayering):
    """The the 2-layer payload with site/global layers concrete.

    Both the site and global data should be updated as they're both
    concrete docs. (2-layer has no region layer.)
    """

    def test_layering_site_and_global_concrete(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
            "_SITE_DATA_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "delete", "path": '.a'}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs,
                                      global_abstract=False)
        site_expected = {'c': 9}
        global_expected = {'a': {'x': 1, 'y': 2}, 'c': 9}
        self._test_layering(documents, site_expected,
                            global_expected=global_expected)


class TestDocumentLayering2Layers2Sites(TestDocumentLayering):

    def test_layering_default_scenario(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_ONE_": {"data": {"b": 4}},
            "_SITE_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_TWO_": {"data": {"b": 3}},
            "_SITE_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".a"}]}
        }

        documents = self._format_data(
            self.FAKE_YAML_DATA_2_LAYERS_2_SITES, kwargs)
        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {'b': 3}]
        self._test_layering(documents, site_expected)

    def test_layering_alternate_scenario(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_ONE_": {"data": {"b": 4}},
            "_SITE_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_TWO_": {"data": {"b": 3}},
            "_SITE_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".a"},
                            {"method": "merge", "path": ".b"}]}
        }

        documents = self._format_data(
            self.FAKE_YAML_DATA_2_LAYERS_2_SITES, kwargs)
        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4}, {'b': 3}]
        self._test_layering(documents, site_expected)


class TestDocumentLayering2Layers2Sites2Globals(TestDocumentLayering):

    def test_layering_two_parents_only_one_with_child(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_ONE_": {"data": {"b": 4}},
            "_SITE_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_TWO_": {"data": {"b": 3}},
            "_SITE_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(
            self.FAKE_YAML_DATA_2_LAYERS_2_SITES, kwargs)

        other_parent = copy.deepcopy(documents[1])
        other_parent['metadata']['labels'] = {'key2': 'value2'}
        documents.append(other_parent)

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {'a': {'x': 1, 'y': 2}, 'b': 3}]
        self._test_layering(documents, site_expected)

    def test_layering_two_parents_one_child_each_1(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_ONE_": {"data": {"b": 4}},
            "_SITE_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_TWO_": {"data": {"b": 3}},
            "_SITE_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(
            self.FAKE_YAML_DATA_2_LAYERS_2_SITES, kwargs)
        # Have the second site reference (created below) ``other_parent``.
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'key2': 'value2'
        }
        other_parent = copy.deepcopy(documents[1])
        other_parent['metadata']['labels'] = {'key2': 'value2'}
        documents.append(other_parent)

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {'a': {'x': 1, 'y': 2}, 'b': 3}]
        self._test_layering(documents, site_expected)

    def test_layering_two_parents_one_child_each_2(self):
        """Scenario:

        Initially: p1: {"a": {"x": 1, "y": 2}}, p2: {"b": {"f": -9, "g": 71}}
        Where: c1 references p1 and c2 references p2
        Merge "." (p1 -> c1): {"a": {"x": 1, "y": 2, "b": 4}}
        Merge "." (p2 -> c2): {"b": {"f": -9, "g": 71}, "c": 3}
        Delete ".c" (p2 -> c2): {"b": {"f": -9, "g": 71}}
        """
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_ONE_": {"data": {"b": 4}},
            "_SITE_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_TWO_": {"data": {"c": 3}},
            "_SITE_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".c"}]}
        }

        documents = self._format_data(
            self.FAKE_YAML_DATA_2_LAYERS_2_SITES, kwargs)
        # Have the second site reference (created below) ``other_parent``.
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'key2': 'value2'
        }
        other_parent = copy.deepcopy(documents[1])
        other_parent['data'] = {"b": {"f": -9, "g": 71}}
        other_parent['metadata']['labels'] = {'key2': 'value2'}
        documents.append(other_parent)

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {"b": {"f": -9, "g": 71}}]
        self._test_layering(documents, site_expected)


class TestDocumentLayering3Layers(TestDocumentLayering):

    def test_layering_default_scenario(self):
        # Default scenario mentioned in design document for 3 layers.
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
        site_expected = {'a': {'z': 3}, 'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_delete_everything(self):
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 3, "y": 4}, "b": 99}},
            "_REGION_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{"path": ".a", "method": "delete"}]},
            "_SITE_ACTIONS_": {"actions": [{"method": "delete", "path": ".b"}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        site_expected = {}
        self._test_layering(documents, site_expected)

    def test_layering_delete_everything_missing_path(self):
        """Scenario:
        
        Initially: {"a": {"x": 3, "y": 4}, "b": 99}
        Delete ".": {}
        Delete ".b": MissingDocumentKey
        """
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 3, "y": 4}, "b": 99}},
            "_REGION_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{"path": ".", "method": "delete"}]},
            "_SITE_ACTIONS_": {"actions": [{"method": "delete", "path": ".b"}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        self._test_layering(
            documents, exception_expected=errors.MissingDocumentKey)

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
        site_expected = {'b': 4}
        self._test_layering(documents, site_expected)

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
        site_expected = {'a': {'z': 5}}
        self._test_layering(documents, site_expected)

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
        site_expected = {'a': {'x': 1, 'y': 2, 'z': 5},
                         'b': {'v': 3, 'w': 4}, 'c': {'e': 55}}
        self._test_layering(documents, site_expected)

    def test_layering_double_merge_2(self):
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {'a': {'e': 55}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'merge'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        site_expected = {'a': {'x': 1, 'y': 2, 'e': 55}, 'b': 4}
        self._test_layering(documents, site_expected)


class TestDocumentLayering3LayersAbstractConcrete(TestDocumentLayering):
    """The the 3-layer payload with site/region layers concrete.

    Both the site and region data should be updated as they're both concrete
    docs.
    """

    def test_layering_site_and_region_concrete(self):
        """Scenario:
        
        Initially: {"a": {"x": 1, "y": 2}}
        Replace ".a": {"a": {"z": 3}} (Region is updated.)
        Merge ".": {"a": {"z": 3}, "b": 4} (Site is updated.)
        """
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}, "b": 5}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{"method": "replace", "path": ".a"}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs,
                                      region_abstract=False)
        site_expected = {'a': {'z': 3}, 'b': 4}
        region_expected = {'a': {'z': 3}}
        self._test_layering(documents, site_expected, region_expected)

    def test_layering_site_region_and_global_concrete(self):
        # Both the site and region data should be updated as they're both
        # concrete docs.
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_": {"data": {"a": {"z": 3}, "b": 5}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{"method": "replace", "path": ".a"}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs,
                                      region_abstract=False,
                                      global_abstract=False)
        site_expected = {'a': {'z': 3}, 'b': 4}
        region_expected = {'a': {'z': 3}}
        # Global data remains unchanged as there's no layer higher than it in
        # this example.
        global_expected = {'a': {'x': 1, 'y': 2}}
        self._test_layering(documents, site_expected, region_expected)


class TestDocumentLayering3LayersScenario(TestDocumentLayering):

    def test_layering_multiple_delete(self):
        """Scenario:
        
        Initially: {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Delete ".": {}
        Delete ".": {}
        Merge ".": {'b': 4}
        """        
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
        site_expected = {'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_1(self):
        """Scenario:
        
        Initially: {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}}
        Merge ".": {'a': {'z': 5}, 'b': 4}
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
        site_expected = {'a': {'z': 5}, 'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_2(self):
        """Scenario:
        
        Initially: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}}
        Replace ".b": {'a': {'z': 5}, 'b': [109]}
        Merge ".": {'a': {'z': 5}, 'b': [32]}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}, 'b': [109]}},
            "_SITE_DATA_": {"data": {"b": [32]}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        site_expected = {'a': {'z': 5}, 'b': [32]}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_3(self):
        """Scenario:
        
        Initially: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        Replace ".b":  {'a': {'z': 5}, 'b': -2, 'c': [123]}
        Merge ".": {'a': {'z': 5}, 'b': 4, 'c': [123]}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4},
                         'c': [123]}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}, 'b': -2, 'c': '_'}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        site_expected = {'a': {'z': 5}, 'b': 4, 'c': [123]}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_4(self):
        """Scenario:
        
        Initially: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        Replace ".b":  {'a': {'z': 5}, 'b': -2, 'c': [123]}
        Replace ".c":  {'a': {'z': 5}, 'b': -2, 'c': '_'}
        Merge ".": {'a': {'z': 5}, 'b': 4, 'c': '_'}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4},
                         'c': [123]}},
            "_REGION_DATA_": {"data": {'a': {'z': 5}, 'b': -2, 'c': '_'}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'},
                            {'path': '.c', 'method': 'replace'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        site_expected = {'a': {'z': 5}, 'b': 4, 'c': '_'}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_delete_replace(self):
        """Scenario:
        
        Initially: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Delete ".a": {'b': {'v': 3, 'w': 4}}
        Replace ".b": {'b': {'z': 3}}
        Delete ".b": {}
        Merge ".": {'b': 4}
        """
        kwargs = {
            "_GLOBAL_DATA_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_": {"data": {"b": {"z": 3}}},
            "_SITE_DATA_": {"data": {"b": 4}},
            "_REGION_ACTIONS_": {
                "actions": [{'path': '.a', 'method': 'delete'},
                            {'path': '.b', 'method': 'replace'},
                            {'path': '.b', 'method': 'delete'}]},
            "_SITE_ACTIONS_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_3_LAYERS, kwargs)
        site_expected = {'b': 4}
        self._test_layering(documents, site_expected)


class TestDocumentLayering3Layers2Regions2Sites(TestDocumentLayering):

    def test_layering_two_parents_only_one_with_child(self):
        """Scenario:

        Initially: r1: {"c": 3, "d": 4}, r2: {"e": 5, "f": 6}
        Merge "." (g -> r1): {"a": 1, "b": 2, "c": 3, "d": 4}
        Merge "." (r1 -> s1): {"a": 1, "b": 2, "c": 3, "d": 4, "g": 7, "h": 8}
        Merge "." (g -> r2): {"a": 1, "b": 2, "e": 5, "f": 6}
        Merge "." (r2 -> s2): {"a": 1, "b": 2, "e": 5, "f": 6, "i": 9, "j": 10}
        """
        kwargs = {
            "_GLOBAL_DATA_": {"data": {"a": 1, "b": 2}},
            "_REGION_DATA_ONE_": {"data": {"c": 3, "d": 4}},
            "_REGION_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_REGION_DATA_TWO_": {"data": {"e": 5, "f": 6}},
            "_REGION_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_ONE_": {"data": {"g": 7, "h": 8}},
            "_SITE_ACTIONS_ONE_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_TWO_": {"data": {"i": 9, "j": 10}},
            "_SITE_ACTIONS_TWO_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

        documents = self._format_data(
            self.FAKE_YAML_DATA_3_LAYERS_2_REGIONS_2_SITES, kwargs)
        site_expected = [{"a": 1, "b": 2, "c": 3, "d": 4, "g": 7, "h": 8},
                         {"a": 1, "b": 2, "e": 5, "f": 6, "i": 9, "j": 10}]
        region_expected = [{"a": 1, "b": 2, "c": 3, "d": 4},
                           {"a": 1, "b": 2, "e": 5, "f": 6}]
        global_expected = {"a": 1, "b": 2}
        self._test_layering(documents, site_expected, region_expected,
                            global_expected)
