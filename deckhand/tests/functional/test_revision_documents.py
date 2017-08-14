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

import yaml

import falcon

from deckhand.tests.functional import base as test_base


class TestRevisionDocumentsApi(test_base.TestFunctionalBase):

    def test_show_revision_documents(self):
        created_document = self.create_document('sample_document')[0]
        revision_id = created_document['revision_id']

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/documents' % revision_id)
        self.assertEqual(falcon.HTTP_200, resp.status)

        retrieved_documents = [d for d in yaml.safe_load_all(resp.text)]
        self.assertEqual(1, len(retrieved_documents))

        for attr in ('schema', 'metadata', 'data'):
            self.assertIn(attr, retrieved_documents[0])
        self.assertEqual(created_document['documents'][0],
                         retrieved_documents[0]['id'])
        self.assertEqual(created_document['revision_id'],
                         retrieved_documents[0]['revision_id'])
