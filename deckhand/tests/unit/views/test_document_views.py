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

from oslo_utils import uuidutils

from deckhand.control.views import document
from deckhand import factories
from deckhand.tests.unit.db import base


class TestRevisionViews(base.TestDbBase):

    def setUp(self):
        super(TestRevisionViews, self).setUp()
        self.view_builder = document.ViewBuilder()
        self.factory = factories.ValidationPolicyFactory()

    def _test_document_creation_view(self, count):
        # Test document creation view with the number of documents being
        # created specified by `count`.
        payload = [base.DocumentFixture.get_minimal_fixture()
                   for _ in range(count)]
        created_documents = self._create_documents(payload)
        document_view = self.view_builder.list(created_documents)

        self.assertIn('documents', document_view)
        self.assertIsInstance(document_view['documents'], list)
        self.assertEqual(count, len(document_view['documents']))

        expected_attrs = ('id', 'revision_id', 'metadata', 'data', 'schema')
        for idx in range(count):
            for attr in expected_attrs:
                self.assertIn(attr, document_view['documents'][idx])
            for attr in ('id', 'revision_id'):
                self.assertTrue(uuidutils.is_uuid_like(
                    document_view['documents'][idx][attr]))

    def test_create_single_document(self):
        self._test_document_creation_view(1)

    def test_create_many_documents(self):
        self._test_document_creation_view(4)
