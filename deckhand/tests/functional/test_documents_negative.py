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

import falcon
from oslo_serialization import jsonutils as json

from deckhand.control import api
from deckhand.tests.functional import base as test_base
from deckhand import types


class TestDocumentsApi(test_base.TestFunctionalBase):

    def test_create_document_without_required_headers(self):
        resp = self.app.simulate_post('/api/v1.0/documents', body=None)
        body = json.loads(resp.text)
        expected_body = {
            "title": "Missing header value",
            "description": "The Content-Type header is required."
        }

        self.assertEqual(falcon.HTTP_400, resp.status)
        self.assertEqual(expected_body, body)

    def test_create_document_with_wrong_content_type_header(self):
        resp = self.app.simulate_post(
            '/api/v1.0/documents', body=None,
            headers={'Content-Type': 'application/json'})
        body = json.loads(resp.text)
        expected_body = {
            "title": "Unsupported media type",
            "description": (
                "Unexpected content type: application/json. Expected content "
                "types are: ['application/x-yaml'].")
        }

        self.assertEqual(falcon.HTTP_415, resp.status)
        self.assertEqual(expected_body, body)
