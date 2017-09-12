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

from deckhand import errors
from deckhand import factories
from deckhand.tests import test_utils
from deckhand.tests.unit.db import base
from deckhand import types


class TestRevisionRollback(base.TestDbBase):

    def test_create_update_rollback(self):
    	# Revision 1: Create 4 documents.
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=4)
        bucket_name = test_utils.rand_name('bucket')
        created_documents = self.create_documents(bucket_name, payload)
        orig_revision_id = created_documents[0]['revision_id']

        # Revision 2: Update the last document.
        payload[-1]['data'] = {'foo': 'bar'}
        updated_documents = self.create_documents(
            bucket_name, payload, do_validation=False)
        new_revision_id = updated_documents[0]['revision_id']

        # Revision 3: rollback to revision 1.
        rollback_revision = self.rollback_revision(orig_revision_id)
        rollback_documents = self.list_revision_documents(
        	rollback_revision['id'])
        revision_ids = [
        	d['revision_id'] for d in rollback_documents]
        orig_revision_ids = [
        	d['orig_revision_id'] for d in rollback_documents]

        self.assertEqual(3, rollback_revision['id'])
        self.assertEqual([1, 1, 1, 1], revision_ids)
        self.assertEqual([1, 1, 1, 1], orig_revision_ids)

    def test_create_update_delete_rollback(self):
    	# Revision 1: Create 4 documents.
        payload = base.DocumentFixture.get_minimal_multi_fixture(count=4)
        bucket_name = test_utils.rand_name('bucket')
        created_documents = self.create_documents(bucket_name, payload)
        orig_revision_id = created_documents[0]['revision_id']

        # Revision 2: Update the first document.
        payload[0]['data'] = {'foo': 'bar'}
        self.create_documents(
            bucket_name, payload, do_validation=False)

        # Revision 3: Delete the last document.
        self.create_documents(
            bucket_name, payload[:-1], do_validation=False)

        # Rollback 4: rollback to revision 1.
        rollback_revision = self.rollback_revision(orig_revision_id)
        rollback_documents = self.list_revision_documents(
        	rollback_revision['id'])
        revision_ids = [
        	d['revision_id'] for d in rollback_documents]
        orig_revision_ids = [
        	d['orig_revision_id'] for d in rollback_documents]

        self.assertEqual(4, rollback_revision['id'])
        self.assertEqual([1, 1, 1, 1], revision_ids)
        self.assertEqual([1, 1, 1, 1], orig_revision_ids)
