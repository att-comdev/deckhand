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


VALIDATION_RESULT = """
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

VALIDATION_RESULT_ALT = """
---
status: failure
errors:
  - documents:
      - schema: promenade/Slaves/v1
        name: kubernetes-slaves
    message: No slave nodes found.
validator:
  name: promenade
  version: 1.1.2
"""


class TestValidationsController(test_base.BaseControllerTest):
    """Test suite for validating positive scenarios for bucket controller."""

    def _create_revision_with_validation_policy(self, payload=None):
        if not payload:
            documents_factory = factories.DocumentFactory(2, [1, 1])
            payload = documents_factory.gen_test({})
        resp = self.app.simulate_put('/api/v1.0/bucket/mop/documents',
                                     body=yaml.safe_dump_all(payload))
        revision_id = list(yaml.safe_load_all(resp.text))[0]['status'][
            'revision']
        return revision_id

    def _create_validation(self, revision_id, validation_name, policy):
        resp = self.app.simulate_post(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            body=policy)
        return resp

    def test_post_validation(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision_with_validation_policy()
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

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
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id)
        self.assertEqual(200, resp.status_code)

        # Validate that the internal deckhand validation was created already.
        body = list(yaml.safe_load_all(resp.text))
        expected_body = [{
            'status': 'failure',
            'validator': {'name': 'promenade', 'version': '1.1.2'}
        }, {
            'status': 'success',
            'validator': {'name': 'deckhand', 'version': '1.0'}
        }]

        self.assertEqual(2, len(body))
        self.assertEqual(sorted(expected_body), sorted(body))

    def test_list_validation_entries(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision_with_validation_policy()
        validation_name = test_utils.rand_name('validation')
        resp = resp = self._create_validation(revision_id, validation_name,
                                              VALIDATION_RESULT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name))
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [{'id': 0, 'status': 'failure'}]
        }
        self.assertEqual(expected_body, body)

    def test_list_validation_entries_with_multiple_entries(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision_with_validation_policy()
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)
        resp = resp = self._create_validation(revision_id, validation_name,
                                              VALIDATION_RESULT_ALT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name))
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 2,
            'results': [
                {'id': 0, 'status': 'failure'}, {'id': 1, 'status': 'failure'}
            ]
        }
        self.assertEqual(expected_body, body)

    def test_show_validation_entry(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:show_validation': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision_with_validation_policy()
        validation_name = test_utils.rand_name('validation')
        resp = resp = self._create_validation(revision_id, validation_name,
                                              VALIDATION_RESULT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s/0' % (revision_id,
                                                         validation_name))
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'name': validation_name,
            'status': 'failure',
            'createdAt': None,
            'expiresAfter': None,
            'errors': [
                {
                    'documents': [
                        {
                            'name': 'node-document-name',
                            'schema': 'promenade/Node/v1'
                        }, {
                            'name': 'kubernetes-masters',
                            'schema': 'promenade/Masters/v1'
                        }
                    ],
                    'message': 'Node has master role, but not included in '
                               'cluster masters list.'
                }
            ]
        }
        self.assertEqual(expected_body, body)

    def test_validation_with_registered_data_schema(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        # Register a `DataSchema` against which the test document will be
        # validated.
        data_schema_factory = factories.DataSchemaFactory()
        metadata_name = 'example/Doc/v1'
        schema_to_use = {
            '$schema': 'http://json-schema.org/schema#',
            'type': 'object',
            'properties': {
                'test': {
                    'type': 'string'
                }
            },
            'required': ['a'],
            'additionalProperties': False
        }
        data_schema = data_schema_factory.gen_test(
            metadata_name, data=schema_to_use)

        revision_id = self._create_revision_with_validation_policy(
            payload=[data_schema])

        # Validate that the internal deckhand validation was created.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id)
        self.assertEqual(200, resp.status_code)
        body = list(yaml.safe_load_all(resp.text))
        expected_body = {
            'status': 'success',
            'validator': {'name': 'deckhand', 'version': '1.0'}
        }
        self.assertEqual(1, len(body))
        self.assertEqual(expected_body, body[0])

        # Create the test document whose data section adheres to the
        # `DataSchema` above.
        doc_factory = factories.DocumentFactory(1, [1])
        doc_to_test = doc_factory.gen_test(
            {'_GLOBAL_DATA_1_': {'data': {'test': 'whatever'}}},
            global_abstract=False)[-1]
        doc_to_test['schema'] = 'example/Doc/v1'
        doc_to_test['metadata']['name'] = 'test_doc'

        revision_id = self._create_revision_with_validation_policy(
            payload=[doc_to_test])

        # Validate that two validations were created.
        # resp = self.app.simulate_get(
        #     '/api/v1.0/revisions/%s/validations' % revision_id)
        # self.assertEqual(200, resp.status_code)
        # body = list(yaml.safe_load_all(resp.text))
        # expected_body = {
        #     'status': 'success',
        #     'validator': {'name': 'deckhand', 'version': '1.0'}
        # }
        # print body
        # self.assertEqual(2, len(body))
        # self.assertEqual(expected_body, body[0])
