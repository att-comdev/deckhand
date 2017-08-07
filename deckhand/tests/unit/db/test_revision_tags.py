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

from deckhand.db.sqlalchemy import api as db_api
from deckhand import errors
from deckhand.tests import test_utils
from deckhand.tests.unit.db import base


class TestRevisionTags(base.TestDbBase):

    def setUp(self):
        super(TestRevisionTags, self).setUp()
        self.revision_id = self._create_revision()

    def _create_revision(self):
        # Automatically creates a revision.
        documents = [base.DocumentFixture.get_minimal_fixture()]
        revision_id = self._create_documents(documents)[0]['revision_id']
        return revision_id

    def test_list_tags(self):
        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEmpty(retrieved_tags)

    def test_create_check_and_list_many_tags(self):
        tags = []
        for _ in range(4):
            tag = test_utils.rand_name(self.__class__.__name__ + '-Tag')
            db_api.revision_tag_create(self.revision_id, tag)
            tags.append(tag)

        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEqual(4, len(retrieved_tags))
        self.assertEqual(tags, retrieved_tags)

        for tag in tags:
            # Should not raise an exception.
            db_api.revision_tag_check(self.revision_id, tag)

    def test_create_and_delete_tags(self):
        tags = []
        for _ in range(4):
            tag = test_utils.rand_name(self.__class__.__name__ + '-Tag')
            db_api.revision_tag_create(self.revision_id, tag)
            tags.append(tag)

        for idx, tag in enumerate(tags):
            expected_tags = tags[idx + 1:]
            result = db_api.revision_tag_delete(self.revision_id, tag)
            self.assertIsNone(result)

            retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
            self.assertEqual(expected_tags, retrieved_tags)

            self.assertRaises(
                errors.RevisionTagNotFound, db_api.revision_tag_check,
                self.revision_id, tag)

    def test_delete_all_tags(self):
        for _ in range(4):
            tag = test_utils.rand_name(self.__class__.__name__ + '-Tag')
            db_api.revision_tag_create(self.revision_id, tag)

        result = db_api.revision_tag_delete_all(self.revision_id)
        self.assertIsNone(result)

        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEmpty(retrieved_tags)

    def test_replace_all_tags(self):
        for _ in range(2):
            tag = test_utils.rand_name(self.__class__.__name__ + '-Tag')
            db_api.revision_tag_create(self.revision_id, tag)

        new_tags = [test_utils.rand_name(self.__class__.__name__ + '-Tag')
                    for _ in range(4)]
        db_api.revision_tag_replace_all(self.revision_id, new_tags)

        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEqual(4, len(retrieved_tags))
        self.assertEqual(new_tags, retrieved_tags)

    def test_delete_all_tags_without_any_tags(self):
        # Validate that no tags exist to begin with.
        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEmpty(retrieved_tags)

        # Validate that deleting all tags without any tags doesn't raise
        # errors.
        db_api.revision_tag_delete_all(self.revision_id)

    def test_replace_all_tags_without_any_tags(self):
        # Validate that no tags exist to begin with.
        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEmpty(retrieved_tags)

        # Validate that deleting all tags without any tags doesn't raise
        # errors.
        db_api.revision_tag_replace_all(self.revision_id, [])

    def test_replace_all_tags_with_empty_list(self):
        """Validate that replacing existing tags with empty mimics deleting
        all the tags."""
        for _ in range(4):
            tag = test_utils.rand_name(self.__class__.__name__ + '-Tag')
            db_api.revision_tag_create(self.revision_id, tag)

        # Validate that replacing all tags with `[]` deletes all tags.
        db_api.revision_tag_replace_all(self.revision_id, [])

        retrieved_tags = db_api.revision_tag_get_all(self.revision_id)
        self.assertEmpty(retrieved_tags)

    def test_create_duplicate_tag(self):
        tag = test_utils.rand_name(self.__class__.__name__ + '-Tag')
        # Create the same tag twice and validate that it returns None the
        # second time.

        db_api.revision_tag_create(self.revision_id, tag)
        resp = db_api.revision_tag_create(self.revision_id, tag)
        self.assertIsNone(resp)
