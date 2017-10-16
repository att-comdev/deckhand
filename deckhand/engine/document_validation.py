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

import re

import jsonschema
from oslo_log import log as logging
from oslo_utils import uuidutils

from deckhand.db.sqlalchemy import api as db_api
from deckhand.engine import document as document_wrapper
from deckhand.engine.schema import base_schema
from deckhand.engine.schema import v1_0
from deckhand import errors
from deckhand import factories
from deckhand import types
from deckhand import utils

LOG = logging.getLogger(__name__)


class DocumentValidation(object):

    def __init__(self, documents):
        """Class for document validation logic for YAML files.

        This class is responsible for validating YAML files according to their
        schema.

        :param documents: Documents to be validated.
        :type documents: List of dictionaries or dictionary.
        """
        if not isinstance(documents, (list, tuple)):
            documents = [documents]
        self.documents = [document_wrapper.Document(d) for d in documents]
        self.validation_policy_factory = factories.ValidationPolicyFactory()

    class SchemaType(object):
        """Class for retrieving correct schema for pre-validation on YAML.

        Retrieves the schema that corresponds to "apiVersion" in the YAML
        data. This schema is responsible for performing pre-validation on
        YAML data.
        """

        schema_versions_info = [
            {'id': 'deckhand/CertificateKey',
             'schema': v1_0.certificate_key_schema},
            {'id': 'deckhand/Certificate',
             'schema': v1_0.certificate_schema},
            {'id': 'deckhand/DataSchema',
             'schema': v1_0.data_schema_schema},
            {'id': 'deckhand/LayeringPolicy',
             'schema': v1_0.layering_policy_schema},
            {'id': 'deckhand/Passphrase',
             'schema': v1_0.passphrase_schema},
            {'id': 'deckhand/ValidationPolicy',
             'schema': v1_0.validation_policy_schema},
            # FIXME(fmontei): Remove this once all Deckhand tests have been
            # refactored to account for dynamic schema registeration via
            # `DataSchema` documents. Otherwise most tests will fail.
            {'id': 'metadata/Document',
             'schema': v1_0.document_schema}]

        schema_re = re.compile(
            '^([A-Za-z]+\/[A-Za-z]+\/v[1]{1}(\.[0]{1}){0,1})$')

        @classmethod
        def _register_data_schemas(cls):
            """Dynamically detect schemas for document validation that have
            been registered by external services via ``DataSchema`` documents.
            """
            data_schemas = db_api.document_get_all(
                schema=types.DATA_SCHEMA_SCHEMA)

            for data_schema in data_schemas:
                if cls.schema_re.match(data_schema['metadata']['name']):
                    schema_id = '/'.join(
                        data_schema['metadata']['name'].split('/')[:2])
                else:
                    schema_id = data_schema['metadata']['name']
                schema_to_use = data_schema['data']
                cls.schema_versions_info.append(
                    {'id': schema_id, 'schema': schema_to_use})  

        @classmethod
        def get_schema(cls, doc):
            """Retrieve the relevant schema based on the document's ``schema``.

            :param doc: The document used for finding the correct schema to
                validate it based on its ``schema``.
            :returns: A schema to be used by ``jsonschema`` for document
                validation, along with the schema's ``metadata.name``.
            :rtype: tuple
            """
            cls._register_data_schemas()

            # FIXME(fmontei): Remove this once all Deckhand tests have been
            # refactored to account for dynamic schema registeration via
            # ``DataSchema`` documents. Otherwise most tests will fail.
            for doc_field in [doc['schema'], doc['metadata']['schema']]:
                schemas = cls._get_schema_by_property(cls.schema_re, doc_field)
                if schemas:
                    return schemas[0], doc_field

            return None, None

        @classmethod
        def _get_schema_by_property(cls, schema_re, field):
            if schema_re.match(field):
                schema_id = '/'.join(field.split('/')[:2])
            else:
                schema_id = field

            matching_schemas = []
            for schema in cls.schema_versions_info:
                if schema_id == schema['id']:
                    if isinstance(schema['schema'], dict):
                        matching_schemas.append(schema['schema'])
                    else:
                        matching_schemas.append(schema['schema'].schema)
            return matching_schemas

    def validate_all(self):
        """Pre-validate that the YAML file is correctly formatted.

        All concrete documents in the revision successfully pass their JSON
        schema validations. The result of the validation is stored under
        the "deckhand-document-schema-validation" validation namespace for
        a document revision.

        Validation is broken up into 2 stages:

            1) Validate that each document contains the basic bulding blocks
               needed: "schema", "metadata" and "data" using a "base" schema.
               Failing this validation is deemed a critical failure, resulting
               in an exception.
            2) Validate each specific document type (e.g. validation policy)
               using a more detailed schema. Failing this validation is deemed
               non-critical, resulting in the error being recorded along with
               any other non-critical exceptions, which are returned together
               later.

        :returns: Tuple, where first entry is a list of validation documents,
            or a list of dictionaries that are of the form of a Deckhand
            ``ValidationPolicy`` and the second entry is a list of exceptions
            that occurred while validating documents. The list of exceptions
            only includes non-critical schema failures.
        :raises errors.InvalidDocumentFormat: If the schema failure is
            critical.
        """
        validation_docs = []
        exceptions = []

        for document in self.documents:
            exc = self._validate_one(document)
            if exc:
                exceptions.append(exc)

        if exceptions:
            deckhand_schema_validation = self._report_failure()
        else:
            deckhand_schema_validation = self._report_success()

        validation_docs.append(deckhand_schema_validation)
        return validation_docs, exceptions

    def _report_success(self):
        deckhand_schema_validation = self.validation_policy_factory.gen(
            types.DECKHAND_SCHEMA_VALIDATION, status='success')
        return deckhand_schema_validation

    def _report_failure(self):
        deckhand_schema_validation = self.validation_policy_factory.gen(
            types.DECKHAND_SCHEMA_VALIDATION, status='failure')
        return deckhand_schema_validation

    def _validate_one(self, document):
        raw_dict = document.to_dict()
        try:
            # Subject every document to basic validation to verify that each
            # main section is present (schema, metadata, data).
            jsonschema.validate(raw_dict, base_schema.schema)
        except jsonschema.exceptions.ValidationError as e:
            LOG.debug('Document failed top-level schema validation. Details: '
                      '%s.', e.message)
            # NOTE(fmontei): We raise here because if we fail basic schema
            # validation, we can't even do policy enforcement correctly which
            # requires checking `metadata.storagePolicy`, which, if missing
            # or malformed, should result in an immediate 400.
            raise errors.InvalidDocumentFormat(
                detail=e.message, schema=e.schema)

        schema_cls, schema_name = self.SchemaType.get_schema(raw_dict)
        if schema_cls is None:
            LOG.debug('Document schema %s not recognized.',
                      document.get_schema())
            return errors.InvalidDocumentSchema(
                document_schema=document.get_schema(),
                schema_list=[
                    s['id'] for s in self.SchemaType.schema_versions_info])

        # Perform more detailed validation on each document depending on
        # its schema. If the document is abstract, validation errors are
        # ignored.
        if document.is_abstract():
            LOG.info('Skipping schema validation for abstract '
                     'document: %s.', document)
        else:
            try:
                jsonschema.validate(raw_dict, schema_cls)
            except jsonschema.exceptions.ValidationError as e:
                    LOG.debug('Document failed %s schema validation. Details: '
                              '%s.', schema_name, e.message)
                    return errors.InvalidDocumentFormat(
                        detail=e.message, schema=e.schema,
                        document_type=document['schema'])
