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

import jsonschema
from oslo_log import log as logging
from oslo_utils import uuidutils
import warlock

from deckhand.engine import document as document_wrapper
from deckhand.engine.schema import base_schema
from deckhand.engine.schema import v1_0
from deckhand import errors
from deckhand import factories
from deckhand import types
from deckhand import utils

LOG = logging.getLogger(__name__)

_DEBUG_SCHEMA = "deckhand/Debug/v1"


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

        # TODO(fmontei): Support dynamically registered schemas.
        schema_versions_info = [
            {'id': 'deckhand/CertificateKey',
             'schema': v1_0.certificate_key_schema},
            {'id': 'deckhand/Certificate',
             'schema': v1_0.certificate_schema},
            {'id': 'deckhand/DataSchema',
             'schema': v1_0.data_schema},
            # NOTE(fmontei): Fall back to the metadata's schema for validating
            # generic documents.
            {'id': 'metadata/Document',
             'schema': v1_0.document_schema},
            {'id': 'deckhand/LayeringPolicy',
             'schema': v1_0.layering_schema},
            {'id': 'deckhand/Passphrase',
             'schema': v1_0.passphrase_schema},
            {'id': 'deckhand/ValidationPolicy',
             'schema': v1_0.validation_schema}]

        def __init__(self, data):
            """Constructor for ``SchemaType``.

            Retrieve the relevant schema based on the API version and schema
            name contained in `document.schema` where `document` constitutes a
            single document in a YAML payload.

            :param api_version: The API version used for schema validation.
            :param schema: The schema property in `document.schema`.
            """
            self.schema = self.get_schema(data)

        def get_schema(self, data):
            # Fall back to `document.metadata.schema` if the schema cannot be
            # determined from `data.schema`.
            for doc_property in [data['schema'], data['metadata']['schema']]:
                schema = self._get_schema_by_property(doc_property)
                if schema:
                    return schema
            return None

        def _get_schema_by_property(self, doc_property):
            schema_parts = doc_property.split('/')
            doc_schema_identifier = '/'.join(schema_parts[:-1])

            for schema in self.schema_versions_info:
                if doc_schema_identifier == schema['id']:
                    return schema['schema'].schema
            return None

    def report_success(self):
        deckhand_schema_validation = self.validation_policy_factory.gen(
            types.DECKHAND_SCHEMA_VALIDATION, status='success')
        return deckhand_schema_validation

    def report_failure(self):
        deckhand_schema_validation = self.validation_policy_factory.gen(
            types.DECKHAND_SCHEMA_VALIDATION, status='failure')
        return deckhand_schema_validation

    def validate_all(self):
        """Pre-validate that the YAML file is correctly formatted.

        All concrete documents in the revision successfully pass their JSON
        schema validations. The result of the validation is stored under
        the "deckhand-document-schema-validation" validation namespace for
        a document revision.

        Validation is broken up into 2 stages:

            1) Validate that each document contains the basic bulding blocks
               needed: "schema", "metadata" and "data" using a "base" schema.
            2) Validate each specific document type (e.g. validation policy)
               using a more detailed schema.

        :returns: Dictionary mapping with keys being the unique name for each
            document and values being the validations executed for that
            document, including failed and succeeded validations.
        """
        internal_validation_docs = []
        original_exc = None

        #import pdb; pdb.set_trace()
        for document in self.documents:
            try:
                self._validate_one(document)
            except errors.InvalidDocumentFormat as e:
                original_exc = e
                deckhand_schema_validation = self.report_failure()
                break

        if not original_exc:
            deckhand_schema_validation = self.report_success()
        internal_validation_docs.append(deckhand_schema_validation)

        return internal_validation_docs, original_exc

    def _validate_one(self, document):
        raw_dict = document.to_dict()
        try:
            # Subject every document to basic validation to verify that each
            # main section is present (schema, metadata, data).
            jsonschema.validate(raw_dict, base_schema.schema)
        except jsonschema.exceptions.ValidationError as e:
            debug_doc = self._create_debug_doc(base_schema.schema, raw_dict)
            error = errors.InvalidDocumentFormat(
                detail=e.message, schema=e.schema)
            return error, debug_doc

        doc_schema_type = self.SchemaType(raw_dict)
        if doc_schema_type.schema is None:
            raise errors.InvalidDocumentFormat(
                document_type=document['schema'])

        # Perform more detailed validation on each document depending on
        # its schema. If the document is abstract, validation errors are
        # ignored.
        try:
            jsonschema.validate(raw_dict, doc_schema_type.schema)
        except jsonschema.exceptions.ValidationError as e:
            # TODO(fmontei): Use the `Document` object wrapper instead
            # once other PR is merged.
            if not document.is_abstract():
                raise errors.InvalidDocumentFormat(
                    detail=e.message, schema=e.schema,
                    document_type=document['schema'])
            else:
                LOG.info('Skipping schema validation for abstract '
                         'document: %s.', document)

    def _create_debug_doc(self, schema, document):
        kwargs = self._gen_debug_doc_kwargs(schema, document, "$", {})
        DebugDocument = warlock.model_factory(schema)   
        debug_document = DebugDocument(**kwargs)
        return debug_document

    def _gen_debug_doc_kwargs(self, schema, data, path, kwargs):
        if 'type' in schema:
            if 'properties' not in schema:
                prop_type = schema['type']
                value = (utils.jsonpath_parse(data, path) or
                         self._gen_debug_message(path, prop_type))
                if 'object' in prop_type:
                    value = {'COERCED_TO_DICT': value}
                return utils.jsonpath_replace(kwargs, value, path)

        for prop in schema.get('properties', {}):
            jsonpath = path + "." + prop
            result = self._gen_debug_doc_kwargs(
                schema['properties'][prop], data, jsonpath, kwargs)
            if result:
                kwargs.update(result)

        return kwargs

    def _gen_debug_message(self, path, type):
        if path == "$.schema":
            return _DEBUG_SCHEMA
        debug_msg = ("DEBUG: This required field (type=%s) is missing." % type)
        if path == '$.metadata.name':
            debug_msg += " EXTRA: %s." % uuidutils.generate_uuid()
        return debug_msg
