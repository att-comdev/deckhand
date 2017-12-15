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
import re

import jsonschema
from oslo_log import log as logging

from deckhand.db.sqlalchemy import api as db_api
from deckhand.engine import document as document_wrapper
from deckhand.engine.schema import base_schema
from deckhand.engine.schema import v1_0
from deckhand import errors
from deckhand import types

LOG = logging.getLogger(__name__)


class DocumentValidation(object):

    def __init__(self, documents):
        """Class for document validation logic for YAML files.

        This class is responsible for validating YAML files according to their
        schema.

        :param documents: Documents to be validated.
        :type documents: list[dict]
        """
        self.documents = []

        if not isinstance(documents, (list, tuple)):
            documents = [documents]

        try:
            for document in documents:
                doc = copy.deepcopy(document)
                # NOTE(fmontei): Remove extraneous top-level keys so that fully
                # rendered documents pass schema validation.
                for key in doc.copy():
                    if key not in ('metadata', 'schema', 'data'):
                        doc.pop(key)
                self.documents.append(document_wrapper.Document(doc))
        except Exception:
            raise errors.InvalidDocumentFormat(
                detail='Document could not be converted into a dictionary',
                schema='Unknown')

    class SchemaType(object):
        """Class for retrieving correct schema for pre-validation on YAML.

        Retrieves the schema that corresponds to "apiVersion" in the YAML
        data. This schema is responsible for performing pre-validation on
        YAML data.
        """

        schema_versions_info = [
            {'id': 'deckhand/CertificateKey',
             'schema': v1_0.certificate_key_schema,
             'version': '1.0'},
            {'id': 'deckhand/Certificate',
             'schema': v1_0.certificate_schema,
             'version': '1.0'},
            {'id': 'deckhand/DataSchema',
             'schema': v1_0.data_schema_schema,
             'version': '1.0'},
            {'id': 'deckhand/LayeringPolicy',
             'schema': v1_0.layering_policy_schema,
             'version': '1.0'},
            {'id': 'deckhand/Passphrase',
             'schema': v1_0.passphrase_schema,
             'version': '1.0'},
            {'id': 'deckhand/ValidationPolicy',
             'schema': v1_0.validation_policy_schema,
             'version': '1.0'}
        ]

        schema_re = re.compile(
            '^([A-Za-z]+\/[A-Za-z]+\/v[1]{1}(\.[0]{1}){0,1})$')

        @classmethod
        def _register_data_schemas(cls):
            """Dynamically detect schemas for document validation that have
            been registered by external services via ``DataSchema`` documents.
            """
            cls.registered_data_schemas = copy.copy(cls.schema_versions_info)

            data_schemas = db_api.document_get_all(
                schema=types.DATA_SCHEMA_SCHEMA, deleted=False)

            for data_schema in data_schemas:
                if cls.schema_re.match(data_schema['metadata']['name']):
                    schema_id = '/'.join(
                        data_schema['metadata']['name'].split('/')[:2])
                else:
                    schema_id = data_schema['metadata']['name']

                validation_schema = copy.deepcopy(v1_0.document_schema.schema)
                validation_schema['properties']['data'] = data_schema['data']

                class Schema(object):
                    schema = validation_schema
                new_entry = {
                    'id': schema_id,
                    'schema': Schema(),
                    'version': '1.0',
                }
                if schema_id not in [
                        s['id'] for s in cls.registered_data_schemas]:
                    cls.registered_data_schemas.append(new_entry)

        @classmethod
        def get_schemas(cls, doc):
            """Retrieve the relevant schema based on the document's ``schema``.

            :param dict doc: The document used for finding the correct schema
                to validate it based on its ``schema``.
            :returns: A schema to be used by ``jsonschema`` for document
                validation.
            :rtype: dict
            """
            cls._register_data_schemas()

            if cls.schema_re.match(doc['schema']):
                schema_id = '/'.join(doc['schema'].split('/')[:2])
            else:
                schema_id = doc['schema']

            matching_schemas = []
            for schema in cls.registered_data_schemas:
                # Can't use `startswith` below to avoid namespace false
                # positives like `CertificateKey` and `Certificate`.
                if schema_id == schema['id']:
                    if schema not in matching_schemas:
                        matching_schemas.append(schema)

            return matching_schemas

    def _format_validation_results(self, results):
        """Format the validation result to be compatible with database
        formatting.

        :results: The validation results generated during document validation.
        :type results: list[dict]
        :returns: List of formatted validation results.
        :rtype: list[dict]
        """
        internal_validator = {
            'name': 'deckhand',
            'version': '1.0'
        }

        formatted_results = []
        for result in results:
            formatted_result = {
                'name': types.DECKHAND_SCHEMA_VALIDATION,
                'status': result['status'],
                'validator': internal_validator,
                'errors': result['errors']
            }
            formatted_results.append(formatted_result)

        return formatted_results

    def _validate_one(self, document):
        raw_dict = document.to_dict()
        try:
            # Subject every document to basic validation to verify that each
            # main section is present (schema, metadata, data).
            jsonschema.validate(raw_dict, base_schema.schema)
        except jsonschema.exceptions.ValidationError as e:
            LOG.debug('Document failed top-level schema validation. Details: '
                      '%s.', e.message)
            # NOTE(fmontei): Raise here because if we fail basic schema
            # validation, then there is no point in continuing.
            raise errors.InvalidDocumentFormat(
                detail=e.message, schema=e.schema)

        schemas_to_use = self.SchemaType.get_schemas(raw_dict)
        if not schemas_to_use:
            LOG.debug('Document schema %s not recognized.',
                      document.get_schema())
            # NOTE(fmontei): Raise here because if Deckhand cannot even
            # determine which schema to use for further validation, then there
            # is no point in trying to continue validation.
            raise errors.InvalidDocumentSchema(
                document_schema=document.get_schema(),
                schema_list=[
                    s['id'] for s in self.SchemaType.schema_versions_info])

        result = {'errors': []}

        # Perform more detailed validation on each document depending on
        # its schema. If the document is abstract, validation errors are
        # ignored.
        if document.is_abstract():
            LOG.info('Skipping schema validation for abstract '
                     'document: %s.', raw_dict)
        else:
            for schema_to_use in schemas_to_use:
                try:
                    schema_validator = schema_to_use['schema'].schema
                    jsonschema.validate(raw_dict, schema_validator)
                # except jsonschema.exceptions.SchemaError as e:
                #     print e
                except jsonschema.exceptions.ValidationError as e:
                    LOG.error(
                        'Document failed schema validation for schema %s.'
                        'Details: %s.', document.get_schema(), e.message)
                    result['errors'].append({
                        'schema': document.get_schema(),
                        'name': document.get_name(),
                        'message': e.message.replace('u\'', '\'')
                    })

        if result['errors']:
            result.setdefault('status', 'failure')
        else:
            result.setdefault('status', 'success')

        return result

    def validate_all(self):
        """Pre-validate that the YAML file is correctly formatted.

        All concrete documents in the revision successfully pass their JSON
        schema validations. The result of the validation is stored under
        the "deckhand-document-schema-validation" validation namespace for
        a document revision.

        Validation is broken up into 2 stages:

            1) Validate that each document contains the basic bulding blocks
               needed: ``schema`` and ``metadata`` using a "base" schema.
               Failing this validation is deemed a critical failure, resulting
               in an exception.

               .. note::

                   The ``data`` section, while mandatory, will not result in
                   critical failure. This is because a document can rely
                   on yet another document for ``data`` substitution. But
                   the validation for the document will be tagged as
                   ``failure``.

            2) Validate each specific document type (e.g. validation policy)
               using a more detailed schema. Failing this validation is deemed
               non-critical, resulting in the error being recorded along with
               any other non-critical exceptions, which are returned together
               later.

        :returns: A list of validations (one for each document validated).
        :rtype: list[dict]
        :raises errors.InvalidDocumentFormat: If the document failed schema
            validation and the failure is deemed critical.
        :raises errors.InvalidDocumentSchema: If no JSON schema for could be
            found for executing document validation.
        """
        validation_results = []

        for document in self.documents:
            result = self._validate_one(document)
            validation_results.append(result)

        validations = self._format_validation_results(validation_results)
        return validations
