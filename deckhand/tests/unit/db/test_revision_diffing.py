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

from deckhand.db.sqlalchemy import api as db_api
from deckhand.tests import test_utils
from deckhand.tests.unit.db import base


class TestRevisionDiffing(base.TestDbBase):

    def test_revision_diff_null(self):
        result = db_api.revision_diff_get(0, 0)
        self.assertEmpty(result)

    def test_revision_diff_created(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        bucket_name = test_utils.rand_name('bucket')
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        result = db_api.revision_diff_get(0, revision_id)
        self.assertEqual({bucket_name: 'created'}, result)

    def test_revision_diff_multi_bucket_created(self):
        revision_ids = []
        bucket_names = []

        for _ in range(3):
            payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
            bucket_name = test_utils.rand_name('bucket')
            bucket_names.append(bucket_name)
            documents = self.create_documents(bucket_name, payload)
            revision_id = documents[0]['revision_id']
            revision_ids.append(revision_id)

        # Between revision 1 and 0, 1 bucket is created.
        result = db_api.revision_diff_get(0, revision_ids[0])
        self.assertEqual({b: 'created' for b in bucket_names[:1]}, result)

        # Between revision 2 and 0, 2 buckets are created.
        result = db_api.revision_diff_get(0, revision_ids[1])
        self.assertEqual({b: 'created' for b in bucket_names[:2]}, result)

        # Between revision 3 and 0, 3 buckets are created.
        result = db_api.revision_diff_get(0, revision_ids[2])
        self.assertEqual({b: 'created' for b in bucket_names}, result)

    def test_revision_diff_self(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        bucket_name = test_utils.rand_name('bucket')
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        result = db_api.revision_diff_get(revision_id, revision_id)
        self.assertEqual({bucket_name: 'unmodified'}, result)

    def test_revision_diff_multi_bucket_self(self):
        bucket_names = []
        revision_ids = []
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)

        for _ in range(3):
            payload[0]['data'] = {'data': test_utils.rand_name('data')}
            bucket_name = test_utils.rand_name('bucket')
            # Store each bucket that was created.
            bucket_names.append(bucket_name)
            documents = self.create_documents(bucket_name, payload)
            # Store each revision that was created.
            revision_id = documents[0]['revision_id']
            revision_ids.append(revision_id)

        # The last revision should contain history for the previous 2 revisions
        # such that its diff history will show history for 3 buckets. Similarly
        # the 2nd revision will have history for 2 buckets and the 1st revision
        # for 1 bucket.
        # 1st revision has revision history for 1 bucket.
        result = db_api.revision_diff_get(revision_ids[0], revision_ids[0])
        self.assertEqual({bucket_names[0]: 'unmodified'}, result)
        # 2nd revision has revision history for 2 buckets.
        result = db_api.revision_diff_get(revision_ids[1], revision_ids[1])
        self.assertEqual({b: 'unmodified' for b in bucket_names[:2]}, result)
        # 3rd revision has revision history for 3 buckets.
        result = db_api.revision_diff_get(revision_ids[2], revision_ids[2])
        self.assertEqual({b: 'unmodified' for b in bucket_names}, result)

    def test_revision_diff_modified(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        bucket_name = test_utils.rand_name('bucket')
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        payload[0]['data'] = {'modified': 'modified'}
        comparison_documents = self.create_documents(bucket_name, payload)
        comparison_revision_id = comparison_documents[0]['revision_id']

        result = db_api.revision_diff_get(revision_id, comparison_revision_id)
        self.assertEqual({bucket_name: 'modified'}, result)

    def test_revision_diff_multi_revision_modified(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        bucket_name = test_utils.rand_name('bucket')
        revision_ids = []

        for _ in range(3):
            payload[0]['data'] = {'modified': test_utils.rand_name('modified')}
            documents = self.create_documents(bucket_name, payload)
            revision_id = documents[0]['revision_id']
            revision_ids.append(revision_id)

        for pair in [(0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1)]:
            result = db_api.revision_diff_get(
                revision_ids[pair[0]], revision_ids[pair[1]])
            self.assertEqual({bucket_name: 'modified'}, result)

    def test_revision_diff_multi_revision_multi_bucket_modified(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        revision_ids = []

        bucket_name = test_utils.rand_name('bucket')
        alt_bucket_name = test_utils.rand_name('bucket')
        bucket_names = [bucket_name, alt_bucket_name]

        # Create revisions while modifying documents in `bucket_name`.
        for bucket_idx in range(2):
            payload[0]['data'] = {'modified': test_utils.rand_name('modified')}
            documents = self.create_documents(
                bucket_names[bucket_idx], payload)
            revision_id = documents[0]['revision_id']
            revision_ids.append(revision_id)

        # Create revisions while modifying documents in `alt_bucket_name`.
        for bucket_idx in range(2):
            payload[0]['data'] = {'modified': test_utils.rand_name('modified')}
            documents = self.create_documents(
                bucket_names[bucket_idx], payload)
            revision_id = documents[0]['revision_id']
            revision_ids.append(revision_id)

        # Between Revisions 0 and 1 bucket_name is unmodified and
        # alt_bucket_name is created.
        result = db_api.revision_diff_get(
            revision_ids[0], revision_ids[1])
        self.assertEqual({bucket_name: 'unmodified',
                          alt_bucket_name: 'created'}, result)

        # Between Revisions 0 and 2 bucket_name is modified (by 2) and
        # alt_bucket_name is created (by 1).
        result = db_api.revision_diff_get(
            revision_ids[0], revision_ids[2])
        self.assertEqual({bucket_name: 'modified',
                          alt_bucket_name: 'created'}, result)

        # Between Revisions 0 and 3 bucket_name is modified (by 2) and
        # alt_bucket_name is created (by 1) (as well as modified by 3).
        result = db_api.revision_diff_get(
            revision_ids[0], revision_ids[3])
        self.assertEqual({bucket_name: 'modified',
                          alt_bucket_name: 'created'}, result)

        # Between Revisions 1 and 2 bucket_name is modified but alt_bucket_name
        # remains unmodified.
        result = db_api.revision_diff_get(
            revision_ids[1], revision_ids[2])
        self.assertEqual({bucket_name: 'modified',
                          alt_bucket_name: 'unmodified'}, result)

        # Between Revisions 1 and 3 bucket_name is modified (by 2) and
        # alt_bucket_name is modified by 3.
        result = db_api.revision_diff_get(
            revision_ids[1], revision_ids[3])
        self.assertEqual({bucket_name: 'modified',
                          alt_bucket_name: 'modified'}, result)

        # Between Revisions 2 and 3 alt_bucket_name is modified but bucket_name
        # remains unmodified.
        result = db_api.revision_diff_get(
            revision_ids[2], revision_ids[3])
        self.assertEqual({bucket_name: 'unmodified',
                          alt_bucket_name: 'modified'}, result)

    def test_revision_diff_ignore_bucket_with_unrelated_documents(self):
        payload = base.DocumentFixture.get_minimal_fixture()
        alt_payload = base.DocumentFixture.get_minimal_fixture()
        bucket_name = test_utils.rand_name('bucket')
        alt_bucket_name = test_utils.rand_name('bucket')

        # Create a bucket with a single document.
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        # Create another bucket with an entirely different document (different
        # schema and metadata.name).
        self.create_documents(alt_bucket_name, alt_payload)

        # Modify the document from the 1st bucket.
        payload['data'] = {'modified': 'modified'}
        documents = self.create_documents(bucket_name, payload)
        comparison_revision_id = documents[0]['revision_id']

        # The `alt_bucket_name` should be ignored.
        result = db_api.revision_diff_get(revision_id, comparison_revision_id)
        self.assertEqual({bucket_name: 'modified'}, result)

    def test_revision_diff_ignore_bucket_with_one_unrelated_documents(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        alt_payload = copy.deepcopy(payload)
        bucket_name = test_utils.rand_name('bucket')
        alt_bucket_name = test_utils.rand_name('bucket')

        # Create a bucket with a single document.
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        # *Only* modify the 1st document from the 1st bucket.
        alt_payload[0]['name'] = test_utils.rand_name('name')
        alt_payload[0]['schema'] = test_utils.rand_name('schema')
        self.create_documents(
            alt_bucket_name, alt_payload, do_validation=False)

        # Modify the document from the 1st bucket.
        payload[0]['data'] = {'modified': 'modified'}
        documents = self.create_documents(bucket_name, payload)
        comparison_revision_id = documents[0]['revision_id']

        # The alt_bucket_name should be included as 2 other documents are
        # shared between the 2 revisions being diffed.
        result = db_api.revision_diff_get(revision_id, comparison_revision_id)
        self.assertEqual({bucket_name: 'modified',
                          alt_bucket_name: 'created'}, result)

    def test_revision_diff_ignore_bucket_with_two_unrelated_documents(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        alt_payload = copy.deepcopy(payload)
        bucket_name = test_utils.rand_name('bucket')
        alt_bucket_name = test_utils.rand_name('bucket')

        # Create a bucket with a single document.
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        # *Only* modify the 1st and 2nd documents from the 1st bucket.
        for idx in range(2):
            alt_payload[idx]['name'] = test_utils.rand_name('name')
            alt_payload[idx]['schema'] = test_utils.rand_name('schema')
        self.create_documents(
            alt_bucket_name, alt_payload, do_validation=False)

        # Modify the document from the 1st bucket.
        payload[0]['data'] = {'modified': 'modified'}
        documents = self.create_documents(bucket_name, payload)
        comparison_revision_id = documents[0]['revision_id']

        # The alt_bucket_name should be included as 1 other document is shared
        # between the 2 revisions being diffed.
        result = db_api.revision_diff_get(revision_id, comparison_revision_id)
        self.assertEqual({bucket_name: 'modified',
                          alt_bucket_name: 'created'}, result)

    def test_revision_diff_ignore_bucket_with_all_unrelated_documents(self):
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=3)
        alt_payload = copy.deepcopy(payload)
        bucket_name = test_utils.rand_name('bucket')
        alt_bucket_name = test_utils.rand_name('bucket')

        # Create a bucket with a single document.
        documents = self.create_documents(bucket_name, payload)
        revision_id = documents[0]['revision_id']

        # Modify all 3 documents from first bucket.
        for idx in range(3):
            alt_payload[idx]['name'] = test_utils.rand_name('name')
            alt_payload[idx]['schema'] = test_utils.rand_name('schema')
        self.create_documents(
            alt_bucket_name, alt_payload, do_validation=False)

        # Modify the document from the 1st bucket.
        payload[0]['data'] = {'modified': 'modified'}
        documents = self.create_documents(bucket_name, payload)
        comparison_revision_id = documents[0]['revision_id']

        # The alt_bucket_name should be excluded as no documents are shared
        # between the revisions being diffed.
        result = db_api.revision_diff_get(revision_id, comparison_revision_id)
        self.assertEqual({bucket_name: 'modified'}, result)
