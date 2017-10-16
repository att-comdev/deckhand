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

import mock
from oslo_config import cfg

from deckhand.control import validations
from deckhand import factories
from deckhand.tests import test_utils
from deckhand.tests.unit.control import base as test_base

CONF = cfg.CONF


VALIDATION_POLICY = """
---
status: failure
errors:
  - documents:
      - schema: promenade/Node/v1
        name: node-document-name
      - schema: promenade/Masters/v1
        name: kubernetes-masters
    message: Node has master role, but not included in cluster masters list.
validator:
  name: promenade
  version: 1.1.2
"""


class TestValidationsController(test_base.BaseControllerTest):
    """Test suite for validating positive scenarios for bucket controller."""

    def _create_revision_with_validation_policy(self):
        documents_factory = factories.DocumentFactory(2, [1, 1])
        payload = documents_factory.gen_test({})
        resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                     body=yaml.safe_dump_all(payload))
        revision_id = list(yaml.safe_load_all(resp.text))[0]['status'][
            'revision']
        return revision_id

    def _create_validation(self, revision_id, validation_name):
        resp = self.app.simulate_post(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            body=VALIDATION_POLICY)
        return resp

    def test_post_validation(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision_with_validation_policy()
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name)

        self.assertEqual(201, resp.status_code)
        expected_body = {
            'status': 'failure',
            'validator': {'name': 'promenade', 'version': '1.1.2'}
        }
        self.assertEqual(expected_body, yaml.safe_load(resp.text))

    def test_list_validations(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision_with_validation_policy()

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id)
        self.assertEqual(200, resp.status_code)

        # Validate that the internal deckhand validation was created already.
        body = list(yaml.safe_load_all(resp.text))
        self.assertEqual(1, len(body))

        # Validate that, after creating a validation policy by an external
        # service, it is listed as well.
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        validation_name = test_utils.rand_name('validation')
        self._create_validation(revision_id, validation_name)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id)
        self.assertEqual(200, resp.status_code)

        # Validate that the internal deckhand validation was created already.
        body = list(yaml.safe_load_all(resp.text))
        print body
        self.assertEqual(2, len(body))
