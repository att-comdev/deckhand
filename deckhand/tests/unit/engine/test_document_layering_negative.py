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
from deckhand.tests.unit.engine import test_document_layering


class TestDocumentLayeringNegative(
        test_document_layering.TestDocumentLayering):

    def test_layering_without_layering_policy(self):
        kwargs = {
            "_GLOBAL_DATA_": {'data': {}}, "_SITE_DATA_": {'data': {}},
            "_SITE_ACTIONS_": {'actions': {}}
        }
        documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs)
        documents.pop(0)  # First doc is layering policy.

        self.assertRaises(errors.LayeringPolicyNotFound,
                          layering.DocumentLayering, documents)

    def test_layering_with_broken_layer_order(self):
        kwargs = {
            "_GLOBAL_DATA_": {'data': {}}, "_SITE_DATA_": {'data': {}},
            "_SITE_ACTIONS_": {'actions': {}}
        }

        documents = self._format_data(self.FAKE_YAML_DATA_2_LAYERS, kwargs)
        broken_layer_orders = [
            ['site', 'region', 'global'], ['broken', 'global'], ['broken'],
            ['site', 'broken']]

        for broken_layer_order in broken_layer_orders:
            documents[0]['data']['layerOrder'] = broken_layer_order
            # The site will not be able to find a correct parent.
            self.assertRaises(errors.MissingDocumentParent,
                              layering.DocumentLayering, documents)
