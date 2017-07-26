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

    def _read_data(self, filename):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_yaml_path = os.path.abspath(os.path.join(
            dir_path, os.pardir, 'resources', filename))

        with open(test_yaml_path, 'r') as yaml_file:
            yaml_data = yaml_file.read()
        return [d for d in yaml.safe_load_all(yaml_data)]

    def _test_layering(self, expected, documents):
        document_layering = layering.DocumentLayering(documents)
        rendered_data = document_layering.render()
        self.assertEqual(expected, rendered_data)


class TestDocumentLayeringBasic(TestDocumentLayering):

    def test_layering_default_scenario(self):
        documents = self._read_data('multi_layer_sample.yaml')
        expected = {'a': {'z': 3}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_method_delete(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'delete'}
        ]

        expected = {'b': 4}
        self._test_layering(expected, documents)

    def test_layering_method_replace(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'replace'}
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'z': 5}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_method_merge_1(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'merge'}
        ]
        documents[2]['data'] = {
            'c': {'e': 55}
        }

        expected = {'a': {'x': 1, 'y': 2}, 'b': 4, 'c': {'e': 55}}
        self._test_layering(expected, documents)

    def test_layering_method_merge_2(self):
        documents = self._read_data('multi_layer_sample.yaml')
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


class TestDocumentLayeringMultiple(TestDocumentLayering):

    def test_layering_multiple_method_delete(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'delete'},
            {'path': '.', 'method': 'delete'}
        ]

        expected = {'b': 4}
        self._test_layering(expected, documents)

    def test_layering_method_replace_1(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'replace'},
            {'path': '.a', 'method': 'replace'},
        ]
        documents[2]['data'] = {
            'a': {'z': 5}
        }

        expected = {'a': {'z': 5}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_multiple_method_replace_2(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}, 'j': {}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.a', 'method': 'replace'},
            {'path': '.b', 'method': 'replace'},
            {'path': '.j', 'method': 'replace'}
        ]
        documents[2]['data'] = {
            'a': {'z': 5}, 'b': {'y': 76}, 'j': {'k': 901}
        }

        expected = {'a': {'z': 5}, 'b': 4, 'j': {'k': 901}}
        self._test_layering(expected, documents)

    def test_layering_replace_multiple(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'][0][
            'path'] = '.'

        expected = {'a': {'z': 3}, 'b': 4}
        self._test_layering(expected, documents)

    def test_layering_multiple_actions(self):
        documents = self._read_data('multi_layer_sample.yaml')
        documents[1]['data'] = {
            'a': {'x': 1, 'y': 2}, 'b': {'v': 3, 'w': 4}
        }
        documents[2]['metadata']['layeringDefinition']['actions'] = [
            {'path': '.', 'method': 'delete'},
            {'path': '.', 'method': 'replace'}
        ]

        expected = {'a': {'z': 3}, 'b': 4}
        self._test_layering(expected, documents)
