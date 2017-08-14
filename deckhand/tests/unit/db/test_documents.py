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

from deckhand import factories
from deckhand.tests import test_utils
from deckhand.tests.unit.db import base


class TestDocuments(base.TestDbBase):

    def setUp(self):
        super(TestDocuments, self).setUp()
        # Will create 3 documents: layering policy, plus a global and site
        # document.
        self.secrets_factory = factories.DocumentSecretFactory()
        self.documents_factory = factories.DocumentFactory(2, [1, 1])
        self.document_mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }

    def test_create_and_get_multiple_document(self):
        documents_payload = self.documents_factory.gen_test(
            self.document_mapping)
        created_documents = self._create_documents(documents_payload)

        self.assertIsInstance(created_documents, list)
        self.assertEqual(3, len(created_documents))

        for idx, document_id in enumerate(
            [d['id'] for d in created_documents]):
            retrieved_document = self._get_document(id=document_id)
            self.assertEqual(created_documents[idx], retrieved_document)

    def test_create_multiple_duplicate_documents_with_no_changes(self):
        documents_payload = self.documents_factory.gen_test(
            self.document_mapping)
        self._create_documents(documents_payload)
        unchanged_documents = self._create_documents(documents_payload)

        self.assertIsInstance(unchanged_documents, list)
        self.assertEmpty(unchanged_documents)

    def test_create_multiple_documents_and_get_revision(self):
        documents_payload = self.documents_factory.gen_test(
            self.document_mapping)
        created_documents = self._create_documents(documents_payload)

        self.assertIsInstance(created_documents, list)
        self.assertEqual(3, len(created_documents))

        # Validate that each document references the same revision.
        revisions = set(d['revision_id'] for d in created_documents)
        self.assertEqual(1, len(revisions))

        # Validate that the revision is valid.
        for document in created_documents:
            revision = self._get_revision(document['revision_id'])
            self._validate_revision(revision)
            self.assertEqual(3, len(revision['documents']))
            self.assertIn(document, revision['documents'])
            self.assertEqual(document['revision_id'], revision['id'])

    def test_get_documents_by_revision_id_and_filters(self):
        documents_payload = self.documents_factory.gen_test(
            self.document_mapping)
        created_documents = self._create_documents(documents_payload)

        for document in created_documents[1:]:
            filters = {
                'schema': document['schema'],
                'metadata.name': document['metadata']['name'],
                'metadata.layeringDefinition.abstract':
                    document['metadata']['layeringDefinition']['abstract'],
                'metadata.layeringDefinition.layer':
                    document['metadata']['layeringDefinition']['layer']
            }
            filtered_documents = self._get_revision_documents(
                document['revision_id'], **filters)
            self.assertEqual(1, len(filtered_documents))
            self.assertEqual(document, filtered_documents[0])

    def test_create_certificate(self):
        rand_secret = {'secret': test_utils.rand_password()}

        for storage_policy in ('encrypted', 'cleartext'):
            secret_doc_payload = self.secrets_factory.gen_test(
                'Certificate', storage_policy, rand_secret)
            created_documents = self._create_documents(secret_doc_payload)

            self.assertEqual(1, len(created_documents))
            self.assertIn('Certificate', created_documents[0]['schema'])
            self.assertEqual(storage_policy, created_documents[0][
                'metadata']['storagePolicy'])
            self.assertTrue(created_documents[0]['is_secret'])
            self.assertEqual(rand_secret, created_documents[0]['data'])

    def test_create_certificate_key(self):
        rand_secret = {'secret': test_utils.rand_password()}

        for storage_policy in ('encrypted', 'cleartext'):
            secret_doc_payload = self.secrets_factory.gen_test(
                'CertificateKey', storage_policy, rand_secret)
            created_documents = self._create_documents(secret_doc_payload)

            self.assertEqual(1, len(created_documents))
            self.assertIn('CertificateKey', created_documents[0]['schema'])
            self.assertEqual(storage_policy, created_documents[0][
                'metadata']['storagePolicy'])
            self.assertTrue(created_documents[0]['is_secret'])
            self.assertEqual(rand_secret, created_documents[0]['data'])

    def test_create_passphrase(self):
        rand_secret = {'secret': test_utils.rand_password()}

        for storage_policy in ('encrypted', 'cleartext'):
            secret_doc_payload = self.secrets_factory.gen_test(
                'Passphrase', storage_policy, rand_secret)
            created_documents = self._create_documents(secret_doc_payload)

            self.assertEqual(1, len(created_documents))
            self.assertIn('Passphrase', created_documents[0]['schema'])
            self.assertEqual(storage_policy, created_documents[0][
                'metadata']['storagePolicy'])
            self.assertTrue(created_documents[0]['is_secret'])
            self.assertEqual(rand_secret, created_documents[0]['data'])
