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
import yaml

from oslo_config import cfg

from deckhand import factories
from deckhand.tests import test_utils
from deckhand.tests.unit.control import base as test_base
from deckhand import types

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
status: success
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

    def _create_revision(self, payload=None):
        if not payload:
            documents_factory = factories.DocumentFactory(2, [1, 1])
            payload = documents_factory.gen_test({})
        resp = self.app.simulate_put(
            '/api/v1.0/buckets/mop/documents',
            headers={'Content-Type': 'application/x-yaml'},
            body=yaml.safe_dump_all(payload))
        self.assertEqual(200, resp.status_code)
        revision_id = list(yaml.safe_load_all(resp.text))[0]['status'][
            'revision']
        return revision_id

    def _create_validation(self, revision_id, validation_name, policy):
        resp = self.app.simulate_post(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            headers={'Content-Type': 'application/x-yaml'}, body=policy)
        return resp

    def test_create_validation(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

        self.assertEqual(201, resp.status_code)
        expected_body = {
            'status': 'failure',
            'validator': {
                'name': 'promenade',
                'version': '1.1.2'
            }
        }
        self.assertEqual(expected_body, yaml.safe_load(resp.text))

    def test_list_validations(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id,
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)

        # Validate that the internal deckhand validation was created already.
        body = list(yaml.safe_load_all(resp.text))
        expected = {
            'count': 1,
            'results': [
                {
                    'status': 'success',
                    'name': types.DECKHAND_SCHEMA_VALIDATION
                }
            ]
        }
        self.assertEqual(1, len(body))
        self.assertEqual(expected, body[0])

        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        # Validate that, after creating a validation policy by an external
        # service, it is listed as well.
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id,
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 2,
            'results': [
                {
                    'name': types.DECKHAND_SCHEMA_VALIDATION,
                    'status': 'success'
                },
                {
                    'name': validation_name,
                    'status': 'failure'
                }
            ]
        }
        self.assertEqual(expected_body, body)

    def test_list_validation_entries(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()

        # Validate that 3 entries (1 for each of the 3 documents created)
        # exists for
        # /api/v1.0/revisions/1/validations/deckhand-schema-validation
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (
                revision_id, types.DECKHAND_SCHEMA_VALIDATION),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 3,
            'results': [{'id': x, 'status': 'success'} for x in range(3)]
        }
        self.assertEqual(expected_body, body)

        # Add the result of a validation to a revision.
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

        # Validate that the entry is present.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [{'id': 0, 'status': 'failure'}]
        }
        self.assertEqual(expected_body, body)

    def test_list_validation_entries_after_creating_validation(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()

        # Add the result of a validation to a revision.
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

        # Validate that the entry is present.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [{'id': 0, 'status': 'failure'}]
        }
        self.assertEqual(expected_body, body)

        # Add the result of another validation to the same revision.
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT_ALT)

        # Validate that 2 entries now exist.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 2,
            'results': [
                {'id': 0, 'status': 'failure'}, {'id': 1, 'status': 'success'}
            ]
        }
        self.assertEqual(expected_body, body)

    def test_list_validation_entries_with_multiple_entries(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()
        validation_name = test_utils.rand_name('validation')
        self._create_validation(revision_id, validation_name,
                                VALIDATION_RESULT)
        self._create_validation(revision_id, validation_name,
                                VALIDATION_RESULT_ALT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (revision_id,
                                                       validation_name),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 2,
            'results': [
                {'id': 0, 'status': 'failure'}, {'id': 1, 'status': 'success'}
            ]
        }
        self.assertEqual(expected_body, body)

    def test_show_validation_entry(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:show_validation': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s/entries/0' % (revision_id,
                                                         validation_name),
            headers={'Content-Type': 'application/x-yaml'})
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

    def test_show_nonexistent_validation_entry_returns_404(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:create_validation': '@',
                 'deckhand:show_validation': '@'}
        self.policy.set_rules(rules)

        revision_id = self._create_revision()
        validation_name = test_utils.rand_name('validation')
        resp = self._create_validation(revision_id, validation_name,
                                       VALIDATION_RESULT)
        self.assertEqual(201, resp.status_code)
        expected_error = ('The requested validation entry 5 was not found for '
                          'validation name %s and revision ID %d.' % (
                              validation_name, revision_id))

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s/entries/5' % (revision_id,
                                                         validation_name),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(404, resp.status_code)
        self.assertEqual(expected_error, yaml.safe_load(resp.text)['message'])

    def test_validation_with_registered_data_schema(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        # Create a `DataSchema` against which the test document will be
        # validated.
        data_schema_factory = factories.DataSchemaFactory()
        metadata_name = 'example/Doc/v1'
        schema_to_use = {
            '$schema': 'http://json-schema.org/schema#',
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'string'
                }
            },
            'required': ['a'],
            'additionalProperties': False
        }
        data_schema = data_schema_factory.gen_test(
            metadata_name, data=schema_to_use)

        # Create the test document whose data section adheres to the
        # `DataSchema` above.
        doc_factory = factories.DocumentFactory(1, [1])
        doc_to_test = doc_factory.gen_test(
            {'_GLOBAL_DATA_1_': {'data': {'a': 'whatever'}}},
            global_abstract=False)[-1]
        doc_to_test['schema'] = 'example/Doc/v1'

        revision_id = self._create_revision(payload=[doc_to_test, data_schema])

        # Validate that the validation was created and succeeded.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id,
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [
                {'name': types.DECKHAND_SCHEMA_VALIDATION, 'status': 'success'}
            ]
        }
        self.assertEqual(expected_body, body)

    def test_validation_with_registered_data_schema_expect_failure(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@'}
        self.policy.set_rules(rules)

        # Create a `DataSchema` against which the test document will be
        # validated.
        data_schema_factory = factories.DataSchemaFactory()
        metadata_name = 'example/foo/v1'
        schema_to_use = {
            '$schema': 'http://json-schema.org/schema#',
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'integer'  # Test doc will fail b/c of wrong type.
                }
            },
            'required': ['a']
        }
        data_schema = data_schema_factory.gen_test(
            metadata_name, data=schema_to_use)

        # Create the test document that fails the validation due to the
        # schema defined by the `DataSchema` document.
        doc_factory = factories.DocumentFactory(1, [1])
        doc_to_test = doc_factory.gen_test(
            {'_GLOBAL_DATA_1_': {'data': {'a': 'fail'}}},
            global_abstract=False)[-1]
        doc_to_test['schema'] = 'example/foo/v1'
        doc_to_test['metadata']['name'] = 'test_doc'

        revision_id = self._create_revision(payload=[doc_to_test, data_schema])

        # Validate that the validation was created and reports failure.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id,
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [
                {'name': types.DECKHAND_SCHEMA_VALIDATION, 'status': 'failure'}
            ]
        }
        self.assertEqual(expected_body, body)

    def test_validation_with_registered_data_schema_expect_multi_failure(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@',
                 'deckhand:show_validation': '@'}
        self.policy.set_rules(rules)

        # Create a `DataSchema` against which the test document will be
        # validated.
        data_schema_factory = factories.DataSchemaFactory()
        metadata_name = 'example/foo/v1'
        schema_to_use = {
            '$schema': 'http://json-schema.org/schema#',
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'integer'  # Test doc will fail b/c of wrong type.
                }
            },
            'required': ['a']
        }
        data_schema = data_schema_factory.gen_test(
            metadata_name, data=schema_to_use)

        # Failure #1.
        # Create the test document that fails the validation due to the
        # schema defined by the `DataSchema` document.
        doc_factory = factories.DocumentFactory(1, [1])
        doc_to_test = doc_factory.gen_test(
            {'_GLOBAL_DATA_1_': {'data': {'a': 'fail'}}},
            global_abstract=False)[-1]
        doc_to_test['schema'] = 'example/foo/v1'
        doc_to_test['metadata']['name'] = 'test_doc'
        # Failure #2.
        # Remove required metadata property, causing error to be generated.
        del doc_to_test['metadata']['layeringDefinition']

        revision_id = self._create_revision(payload=[doc_to_test, data_schema])

        # Validate that the validation was created and reports failure.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id,
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [
                {'name': types.DECKHAND_SCHEMA_VALIDATION, 'status': 'failure'}
            ]
        }
        self.assertEqual(expected_body, body)

        # Validate that both expected errors are present for validation.
        expected_errors = [
            {
                'message': "'layeringDefinition' is a required property",
                'name': 'test_doc',
                'schema': 'example/foo/v1'
            }, {
                'message': "'fail' is not of type 'integer'",
                'name': 'test_doc',
                'schema': 'example/foo/v1'
            }
        ]
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s/entries/0' % (
                revision_id, types.DECKHAND_SCHEMA_VALIDATION),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)

        self.assertEqual('failure', body['status'])
        self.assertEqual(expected_errors, body['errors'])

    def test_validation_with_registered_data_schema_expect_mixed(self):
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@',
                 'deckhand:show_validation': '@'}
        self.policy.set_rules(rules)

        # Create a `DataSchema` against which the test document will be
        # validated.
        data_schema_factory = factories.DataSchemaFactory()
        metadata_name = 'example/foo/v1'
        schema_to_use = {
            '$schema': 'http://json-schema.org/schema#',
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'integer'  # Test doc will fail b/c of wrong type.
                }
            },
            'required': ['a']
        }
        data_schema = data_schema_factory.gen_test(
            metadata_name, data=schema_to_use)

        # Create a document that passes validation and another that fails it.
        doc_factory = factories.DocumentFactory(1, [1])
        fail_doc = doc_factory.gen_test(
            {'_GLOBAL_DATA_1_': {'data': {'a': 'fail'}}},
            global_abstract=False)[-1]
        fail_doc['schema'] = 'example/foo/v1'
        fail_doc['metadata']['name'] = 'test_doc'

        pass_doc = copy.deepcopy(fail_doc)
        pass_doc['data']['a'] = 5

        revision_id = self._create_revision(
            payload=[fail_doc, pass_doc, data_schema])

        # Validate that the validation reports failure since `fail_doc`
        # should've failed validation.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations' % revision_id,
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 1,
            'results': [
                {'name': types.DECKHAND_SCHEMA_VALIDATION, 'status': 'failure'}
            ]
        }
        self.assertEqual(expected_body, body)

        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (
                revision_id, types.DECKHAND_SCHEMA_VALIDATION),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 3,
            'results': [{'id': 0, 'status': 'failure'},  # fail_doc failed.
                        {'id': 1, 'status': 'success'},  # DataSchema passed.
                        {'id': 2, 'status': 'success'}]  # pass_doc succeeded.
        }
        self.assertEqual(expected_body, body)

        # Validate that fail_doc validation failed for the expected reason.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s/entries/0' % (
                revision_id, types.DECKHAND_SCHEMA_VALIDATION),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_errors = [{
            'schema': 'example/foo/v1',
            'name': 'test_doc',
            'message': "'fail' is not of type 'integer'"
        }]
        self.assertIn('errors', body)
        self.assertEqual(expected_errors, body['errors'])

    def test_document_without_data_section_saves_but_fails_validation(self):
        """Validate that a document without the data section is saved to the
        database, but fails validation. This is a valid use case because a
        document in a bucket can be created without a data section, which
        depends on substitution from another document.
        """
        rules = {'deckhand:create_cleartext_documents': '@',
                 'deckhand:list_validations': '@',
                 'deckhand:show_validation': '@'}
        self.policy.set_rules(rules)

        documents_factory = factories.DocumentFactory(1, [1])
        document = documents_factory.gen_test({}, global_abstract=False)[-1]
        del document['data']

        data_schema_factory = factories.DataSchemaFactory()
        data_schema = data_schema_factory.gen_test(document['schema'], {})

        revision_id = self._create_revision(payload=[document, data_schema])

        # Validate that the entry is present.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s' % (
                revision_id, types.DECKHAND_SCHEMA_VALIDATION),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)

        body = yaml.safe_load(resp.text)
        expected_body = {
            'count': 2,
            'results': [{'id': 0, 'status': 'failure'},  # Document.
                        {'id': 1, 'status': 'success'}]  # DataSchema.
        }
        self.assertEqual(expected_body, body)

        # Validate that the created document failed validation for the expected
        # reason.
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/validations/%s/entries/0' % (
                revision_id, types.DECKHAND_SCHEMA_VALIDATION),
            headers={'Content-Type': 'application/x-yaml'})
        self.assertEqual(200, resp.status_code)
        body = yaml.safe_load(resp.text)
        expected_errors = [{
            'schema': document['schema'],
            'name': document['metadata']['name'],
            'message': "'data' is a required property"
        }]
        self.assertIn('errors', body)
        self.assertEqual(expected_errors, body['errors'])
