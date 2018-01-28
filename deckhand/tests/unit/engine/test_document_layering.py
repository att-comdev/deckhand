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

from deckhand.engine import layering
from deckhand import errors
from deckhand import factories
from deckhand.tests.unit import base as test_base
from deckhand import types


class TestDocumentLayering(test_base.DeckhandTestCase):

    def _test_layering(self, documents, site_expected=None,
                       region_expected=None, global_expected=None,
                       exception_expected=None, substitution_sources=None):
        document_layering = layering.DocumentLayering(
            documents, substitution_sources)

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
            # No need to validate the LayeringPolicy: it remains unchanged.
            if doc['schema'].startswith(types.LAYERING_POLICY_SCHEMA):
                continue
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
                self.assertEqual(expected, site_docs[idx].get('data'),
                                 'Actual site data does not match expected.')
        if region_expected:
            if not isinstance(region_expected, list):
                region_expected = [region_expected]

            for idx, expected in enumerate(region_expected):
                self.assertEqual(expected, region_docs[idx].get('data'),
                                 'Actual region data does not match expected.')
        if global_expected:
            if not isinstance(global_expected, list):
                global_expected = [global_expected]

            for idx, expected in enumerate(global_expected):
                self.assertEqual(expected, global_docs[idx].get('data'),
                                 'Actual global data does not match expected.')


class TestDocumentLayering2Layers(TestDocumentLayering):

    def test_layering_default_scenario(self):
        # Default scenario mentioned in design document for 2 layers (region
        # data is removed).
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_default_scenario_multi_parentselector(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        # Test case where the same number of labels are found in parent
        # labels and child's parentSelector.
        labels = {'foo': 'bar', 'baz': 'qux'}
        documents[1]['metadata']['labels'] = labels
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = (
            labels)
        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(documents, site_expected)

        # Test case where child's parentSelector is a subset of parent's
        # labels.
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'foo': 'bar'}
        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(documents, site_expected)

        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'baz': 'qux'}
        site_expected = {'a': {'x': 1, 'y': 2}, 'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_default_scenario_multi_parentselector_no_match(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        labels = {'a': 'b', 'c': 'd'}
        documents[1]['metadata']['labels'] = labels

        # Test case where none of the labels in parentSelector match.
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'w': 'x', 'y': 'z'
        }
        self._test_layering(documents, site_expected={})

        # Test case where parentSelector has one too many labels to be a match.
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'a': 'b', 'c': 'd', 'e': 'f'
        }
        self._test_layering(documents, site_expected={})

        # Test case where parentSelector keys match (but not values).
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'a': 'x', 'c': 'y'
        }
        self._test_layering(documents, site_expected={})

        # Test case where parentSelector values match (but not keys).
        documents[-1]['metadata']['layeringDefinition']['parentSelector'] = {
            'x': 'b', 'y': 'd'
        }
        self._test_layering(documents, site_expected={})

    def test_layering_method_delete(self):
        site_expected = [{}, {'c': 9}, {"a": {"x": 1, "y": 2}}]
        doc_factory = factories.DocumentFactory(2, [1, 1])

        for idx, path in enumerate(['.', '.a', '.c']):
            mapping = {
                "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
                "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
                "_SITE_ACTIONS_1_": {
                    "actions": [{"method": "delete", "path": path}]}
            }
            documents = doc_factory.gen_test(mapping, site_abstract=False)
            self._test_layering(documents, site_expected[idx])

    def test_layering_method_merge(self):
        site_expected = [
            {'a': {'x': 7, 'y': 2, 'z': 3}, 'b': 4, 'c': 9},
            {'a': {'x': 7, 'y': 2, 'z': 3}, 'c': 9},
            {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': 9}
        ]
        doc_factory = factories.DocumentFactory(2, [1, 1])

        for idx, path in enumerate(['.', '.a', '.b']):
            mapping = {
                "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
                "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
                "_SITE_ACTIONS_1_": {
                    "actions": [{"method": "merge", "path": path}]}
            }
            documents = doc_factory.gen_test(mapping, site_abstract=False)
            self._test_layering(documents, site_expected[idx])

    def test_layering_method_replace(self):
        site_expected = [
            {'a': {'x': 7, 'z': 3}, 'b': 4},
            {'a': {'x': 7, 'z': 3}, 'c': 9},
            {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': 9}
        ]
        doc_factory = factories.DocumentFactory(2, [1, 1])

        for idx, path in enumerate(['.', '.a', '.b']):
            mapping = {
                "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
                "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
                "_SITE_ACTIONS_1_": {
                    "actions": [{"method": "replace", "path": path}]}
            }
            documents = doc_factory.gen_test(mapping, site_abstract=False)
            self._test_layering(documents, site_expected[idx])

    def test_layering_documents_with_different_schemas_do_not_layer(self):
        """Validates that documents with different schemas are not layered
        together.
        """
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)
        documents[1]['schema'] = 'deckhand/Document/v1'
        documents[2]['schema'] = 'deckhand/Document/v2'

        global_expected = {"a": {"x": 1, "y": 2}}
        site_expected = {'b': 4}
        self._test_layering(documents, site_expected=site_expected,
                            global_expected=global_expected)


class TestDocumentLayering2LayersAbstractConcrete(TestDocumentLayering):
    """The the 2-layer payload with site/global layers concrete.

    Both the site and global data should be updated as they're both
    concrete docs. (2-layer has no region layer.)
    """

    def test_layering_site_and_global_concrete(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
            "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "delete", "path": '.a'}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False,
                                         global_abstract=False)

        site_expected = {'c': 9}
        global_expected = {'a': {'x': 1, 'y': 2}, 'c': 9}
        self._test_layering(documents, site_expected,
                            global_expected=global_expected)

    def test_layering_site_and_global_abstract(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}, "c": 9}},
            "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "delete", "path": '.a'}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=True,
                                         global_abstract=True)

        site_expected = {"a": {"x": 7, "z": 3}, "b": 4}
        global_expected = {'a': {'x': 1, 'y': 2}, 'c': 9}
        self._test_layering(documents, site_expected,
                            global_expected=global_expected)


class TestDocumentLayering2Layers2Sites(TestDocumentLayering):

    def test_layering_default_scenario(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"b": 3}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".a"}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 2])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {'b': 3}]
        self._test_layering(documents, site_expected)

    def test_layering_alternate_scenario(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"b": 3}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".a"},
                            {"method": "merge", "path": ".b"}]}
        }
        doc_factory = factories.DocumentFactory(2, [1, 2])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4}, {'b': 3}]
        self._test_layering(documents, site_expected)


class TestDocumentLayering2Layers2Sites2Globals(TestDocumentLayering):

    def test_layering_two_parents_only_one_with_child(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_GLOBAL_DATA_2_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"b": 3}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [2, 2])
        documents = doc_factory.gen_test(
            mapping, site_abstract=False, site_parent_selectors=[
                {'global': 'global1'}, {'global': 'global2'}])

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {'a': {'x': 1, 'y': 2}, 'b': 3}]
        self._test_layering(documents, site_expected)

    def test_layering_two_parents_one_child_each_1(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_GLOBAL_DATA_2_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"b": 3}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(2, [2, 2])
        documents = doc_factory.gen_test(
            mapping, site_abstract=False, site_parent_selectors=[
                {'global': 'global1'}, {'global': 'global2'}])

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
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_GLOBAL_DATA_2_": {"data": {"b": {"f": -9, "g": 71}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"c": 3}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".c"}]}
        }
        doc_factory = factories.DocumentFactory(2, [2, 2])
        documents = doc_factory.gen_test(
            mapping, site_abstract=False, site_parent_selectors=[
                {'global': 'global1'}, {'global': 'global2'}])

        site_expected = [{'a': {'x': 1, 'y': 2}, 'b': 4},
                         {"b": {"f": -9, "g": 71}}]
        self._test_layering(documents, site_expected)


class TestDocumentLayering3Layers(TestDocumentLayering):

    def test_layering_default_scenario(self):
        # Default scenario mentioned in design document for 3 layers.
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "replace", "path": ".a"}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'a': {'z': 3}, 'b': 4}
        region_expected = {"a": {"z": 3}}  # Region is abstract.
        self._test_layering(documents, site_expected, region_expected)

    def test_layering_delete_everything(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 3, "y": 4}, "b": 99}},
            "_REGION_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"path": ".a", "method": "delete"}]},
            "_SITE_ACTIONS_1_": {"actions": [
                {"method": "delete", "path": ".b"}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {}
        self._test_layering(documents, site_expected)

    def test_layering_delete_everything_missing_path(self):
        """Scenario:

        Initially: {"a": {"x": 3, "y": 4}, "b": 99}
        Delete ".": {}
        Delete ".b": MissingDocumentKey
        """
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 3, "y": 4}, "b": 99}},
            "_REGION_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"path": ".", "method": "delete"}]},
            "_SITE_ACTIONS_1_": {"actions": [
                {"method": "delete", "path": ".b"}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        self._test_layering(
            documents, exception_expected=errors.MissingDocumentKey)

    def test_layering_delete_path_a(self):
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'delete'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_merge_and_replace(self):
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_1_": {"data": {'a': {'z': 5}}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.', 'method': 'replace'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'a': {'z': 5}}
        self._test_layering(documents, site_expected)

    def test_layering_double_merge(self):
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"c": {"e": 55}}},
            "_REGION_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_SITE_DATA_1_": {"data": {"a": {"z": 5}}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_ACTIONS_1_": {"actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'a': {'x': 1, 'y': 2, 'z': 5},
                         'b': {'v': 3, 'w': 4}, 'c': {'e': 55}}
        self._test_layering(documents, site_expected)

    def test_layering_double_merge_2(self):
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {'a': {'e': 55}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'merge'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

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
        Merge ".": {"a": {"x": 1, "y": 2, "z": 3}, "b": 5, "c": 11}
            (Region updated.)
        Delete ".c": {"a": {"x": 1, "y": 2, "z": 3}, "b": 5} (Region updated.)
        Replace ".b": {"a": {"x": 1, "y": 2, "z": 3}, "b": 4} (Site updated.)
        """
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}, "b": 5, "c": 11}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".c"}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "replace", "path": ".b"}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False,
                                    region_abstract=False)

        site_expected = {"a": {"x": 1, "y": 2, "z": 3}, "b": 4}
        region_expected = {"a": {"x": 1, "y": 2, "z": 3}, "b": 5}
        self._test_layering(documents, site_expected, region_expected)

    def test_layering_site_concrete_and_region_abstract(self):
        """Scenario:

        Initially: {"a": {"x": 1, "y": 2}}
        Merge ".": {"a": {"x": 1, "y": 2, "z": 3}, "b": 5, "c": 11}
        Delete ".c": {"a": {"x": 1, "y": 2, "z": 3}, "b": 5}
        Replace ".b": {"a": {"x": 1, "y": 2, "z": 3}, "b": 4} (Site updated.)
        """
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}, "b": 5, "c": 11}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."},
                            {"method": "delete", "path": ".c"}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "replace", "path": ".b"}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False,
                                    region_abstract=True)

        site_expected = {"a": {"x": 1, "y": 2, "z": 3}, "b": 4}
        region_expected = {"a": {"z": 3}, "b": 5, "c": 11}
        self._test_layering(documents, site_expected, region_expected)

    def test_layering_site_region_and_global_concrete(self):
        # Both the site and region data should be updated as they're both
        # concrete docs.
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}, "b": 5}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "replace", "path": ".a"}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(
            mapping, site_abstract=False, region_abstract=False,
            global_abstract=False)

        site_expected = {'a': {'z': 3}, 'b': 4}
        region_expected = {'a': {'z': 3}}
        # Global data remains unchanged as there's no layer higher than it in
        # this example.
        global_expected = {'a': {'x': 1, 'y': 2}}
        self._test_layering(documents, site_expected, region_expected,
                            global_expected)


class TestDocumentLayering3LayersScenario(TestDocumentLayering):

    def test_layering_multiple_delete(self):
        """Scenario:

        Initially: {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Delete ".": {}
        Delete ".": {}
        Merge ".": {'b': 4}
        """
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {"a": {"z": 3}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.', 'method': 'delete'},
                            {'path': '.', 'method': 'delete'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_1(self):
        """Scenario:

        Initially: {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}}
        Merge ".": {'a': {'z': 5}, 'b': 4}
        """
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {'a': {'z': 5}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.a', 'method': 'replace'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'a': {'z': 5}, 'b': 4}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_2(self):
        """Scenario:

        Initially: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}}
        Replace ".b": {'a': {'z': 5}, 'b': [109]}
        Merge ".": {'a': {'z': 5}, 'b': [32]}
        """
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {'a': {'z': 5}, 'b': [109]}},
            "_SITE_DATA_1_": {"data": {"b": [32]}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'a': {'z': 5}, 'b': [32]}
        self._test_layering(documents, site_expected)

    def test_layering_multiple_replace_3(self):
        """Scenario:

        Initially: {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        Replace ".a": {'a': {'z': 5}, 'b': {'v': 3, 'w': 4}, 'c': [123]}
        Replace ".b":  {'a': {'z': 5}, 'b': -2, 'c': [123]}
        Merge ".": {'a': {'z': 5}, 'b': 4, 'c': [123]}
        """
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4},
                         'c': [123]}},
            "_REGION_DATA_1_": {"data": {'a': {'z': 5}, 'b': -2, 'c': '_'}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

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
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4},
                         'c': [123]}},
            "_REGION_DATA_1_": {"data": {'a': {'z': 5}, 'b': -2, 'c': '_'}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'replace'},
                            {'path': '.b', 'method': 'replace'},
                            {'path': '.c', 'method': 'replace'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

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
        mapping = {
            "_GLOBAL_DATA_1_": {
                "data": {'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}}},
            "_REGION_DATA_1_": {"data": {"b": {"z": 3}}},
            "_SITE_DATA_1_": {"data": {"b": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{'path': '.a', 'method': 'delete'},
                            {'path': '.b', 'method': 'replace'},
                            {'path': '.b', 'method': 'delete'}]},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 1, 1])
        documents = doc_factory.gen_test(mapping, site_abstract=False)

        site_expected = {'b': 4}
        self._test_layering(documents, site_expected)


class TestDocumentLayering3Layers2Regions2Sites(TestDocumentLayering):

    def test_layering_two_abstract_regions_one_child_each(self):
        """Scenario:

        Initially: r1: {"c": 3, "d": 4}, r2: {"e": 5, "f": 6}
        Merge "." (g -> r1): {"a": 1, "b": 2, "c": 3, "d": 4}
        Merge "." (r1 -> s1): {"a": 1, "b": 2, "c": 3, "d": 4, "g": 7, "h": 8}
        Merge "." (g -> r2): {"a": 1, "b": 2, "e": 5, "f": 6}
        Merge "." (r2 -> s2): {"a": 1, "b": 2, "e": 5, "f": 6, "i": 9, "j": 10}
        """
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": 1, "b": 2}},
            "_REGION_DATA_1_": {"data": {"c": 3, "d": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_REGION_DATA_2_": {"data": {"e": 5, "f": 6}},
            "_REGION_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_1_": {"data": {"g": 7, "h": 8}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"i": 9, "j": 10}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 2, 2])
        documents = doc_factory.gen_test(
            mapping, region_abstract=True, site_abstract=False,
            site_parent_selectors=[
                {'region': 'region1'}, {'region': 'region2'}])

        site_expected = [{"a": 1, "b": 2, "c": 3, "d": 4, "g": 7, "h": 8},
                         {"a": 1, "b": 2, "e": 5, "f": 6, "i": 9, "j": 10}]
        region_expected = [{"c": 3, "d": 4}, {"e": 5, "f": 6}]
        global_expected = {"a": 1, "b": 2}
        self._test_layering(documents, site_expected, region_expected,
                            global_expected)

    def test_layering_two_concrete_regions_one_child_each(self):
        """Scenario:

        Initially: r1: {"c": 3, "d": 4}, r2: {"e": 5, "f": 6}
        Merge "." (g -> r1): {"a": 1, "b": 2, "c": 3, "d": 4}
        Merge "." (r1 -> s1): {"a": 1, "b": 2, "c": 3, "d": 4, "g": 7, "h": 8}
        Merge "." (g -> r2): {"a": 1, "b": 2, "e": 5, "f": 6}
        Merge "." (r2 -> s2): {"a": 1, "b": 2, "e": 5, "f": 6, "i": 9, "j": 10}
        """
        mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": 1, "b": 2}},
            "_REGION_DATA_1_": {"data": {"c": 3, "d": 4}},
            "_REGION_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_REGION_DATA_2_": {"data": {"e": 5, "f": 6}},
            "_REGION_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_1_": {"data": {"g": 7, "h": 8}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]},
            "_SITE_DATA_2_": {"data": {"i": 9, "j": 10}},
            "_SITE_ACTIONS_2_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        doc_factory = factories.DocumentFactory(3, [1, 2, 2])
        documents = doc_factory.gen_test(
            mapping, region_abstract=False, site_abstract=False,
            site_parent_selectors=[
                {'region': 'region1'}, {'region': 'region2'}])

        site_expected = [{"a": 1, "b": 2, "c": 3, "d": 4, "g": 7, "h": 8},
                         {"a": 1, "b": 2, "e": 5, "f": 6, "i": 9, "j": 10}]
        region_expected = [{"a": 1, "b": 2, "c": 3, "d": 4},
                           {"a": 1, "b": 2, "e": 5, "f": 6}]
        global_expected = {"a": 1, "b": 2}
        self._test_layering(documents, site_expected, region_expected,
                            global_expected)
