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

from deckhand.tests.functional import base as test_base
from deckhand import types


class TestDocumentsApi(test_base.TestFunctionalBase):

    def test_create_document(self):
        resp_documents = self.create_document('sample_document')
        expected_validation_policy = self.validation_policy_factory.gen(
            types.DECKHAND_SCHEMA_VALIDATION, status='success')

        # Validate that the correct number of documents were created: one
        # document corresponding to ``yaml_data``.
        self.assertEqual(1, len(resp_documents))
        self.assertIn('revision_id', resp_documents[0])
