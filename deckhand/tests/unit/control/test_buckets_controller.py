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

from oslo_config import cfg

from deckhand import factories
from deckhand.tests.unit.control import base as test_base

CONF = cfg.CONF


class TestBucketsController(test_base.BaseControllerTest):
    """Test suite for validating positive scenarios for bucket controller."""

    def test_put_bucket(self):
        documents_factory = factories.DocumentFactory(2, [1, 1])
        document_mapping = {
            "_GLOBAL_DATA_1_": {"data": {"a": {"x": 1, "y": 2}}},
            "_SITE_DATA_1_": {"data": {"a": {"x": 7, "z": 3}, "b": 4}},
            "_SITE_ACTIONS_1_": {
                "actions": [{"method": "merge", "path": "."}]}
        }
        payload = documents_factory.gen_test(document_mapping)

        resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                     body=yaml.safe_dump_all(payload))
        self.assertEqual(200, resp.status_code)
        created_documents = list(yaml.safe_load_all(resp.text))
        self.assertEqual(3, len(created_documents))
        expected = sorted([(d['schema'], d['metadata']['name'])
                           for d in payload])
        actual = sorted([(d['schema'], d['metadata']['name'])
                         for d in created_documents])
        self.assertEqual(expected, actual)

    def test_put_bucket_with_secret(self):
        secrets_factory = factories.DocumentSecretFactory()
        payload = [secrets_factory.gen_test('Certificate', 'cleartext')]

        resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                     body=yaml.safe_dump_all(payload))
        self.assertEqual(200, resp.status_code)
        created_documents = list(yaml.safe_load_all(resp.text))
        self.assertEqual(1, len(created_documents))
        expected = sorted([(d['schema'], d['metadata']['name'])
                           for d in payload])
        actual = sorted([(d['schema'], d['metadata']['name'])
                         for d in created_documents])
        self.assertEqual(expected, actual)
        self.assertEqual({'secret': payload[0]['data']},
                         created_documents[0]['data'])


class TestBucketsControllerNegative(test_base.BaseControllerTest):
    """Test suite for validating negative scenarios for bucket controller."""

    def test_put_bucket_with_invalid_document_payload(self):
        no_colon_spaces = """
name:foo
schema:
    layeringDefinition:
        layer:site
"""
        invalid_payloads = ['garbage', no_colon_spaces]
        error_re = ['.*The provided YAML failed schema validation.*',
                    '.*mapping values are not allowed here.*']

        for idx, payload in enumerate(invalid_payloads):
            resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                         body=payload)
            self.assertEqual(400, resp.status_code)
            self.assertRegexpMatches(resp.text, error_re[idx])


class TestBucketsControllerNegativeRBAC(test_base.BaseAdminControllerTest):
    """Test suite for validating negative RBAC scenarios for bucket
    controller.
    """

    def test_put_bucket_cleartext_secret_except_forbidden(self):
        documents_factory = factories.DocumentFactory(2, [1, 1])
        payload = documents_factory.gen_test({})

        resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                     body=yaml.safe_dump_all(payload))
        self.assertEqual(403, resp.status_code)

    def test_put_bucket_encrypted_secret_except_forbidden(self):
        secrets_factory = factories.DocumentSecretFactory()
        payload = [secrets_factory.gen_test('Certificate', 'encrypted')]

        resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                     body=yaml.safe_dump_all(payload))
        self.assertEqual(403, resp.status_code)
