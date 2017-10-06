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
import warlock

from deckhand.db.sqlalchemy import api as db_api
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
             'schema': v1_0.validation_policy_schema}]

        def __init__(self, data):
            """Constructor for ``SchemaType``.

            Retrieve the relevant schema based on the API version and schema
            name contained in `document.schema` where `document` constitutes a
            single document in a YAML payload.

            :param api_version: The API version used for schema validation.
            :param schema: The schema property in `document.schema`.
            """
            schema_re = re.compile(
                '^([A-Za-z]+\/[A-Za-z]+\/v[1]{1}(\.[0]{1}){0,1})$')
            data_schemas = db_api.documents_get_all(
                schema='deckhand/DataSchema/v1')

            for data_schema in data_schemas:
                if schema_re.match(data_schema['metadata']['name']):
                    schema_id = '/'.join(
                        data_schema['metadata']['name'].split('/')[:2])
                else:
                    schema_id = data_schema['metadata']['name']
                schema_ref = data_schema['data']['$schema']
                actual_schema = getattr(v1_0, schema_ref, None)
                self.schema_versions_info.append(
                    {'id': schema_id, 'schema': actual_schema})

            if schema_re.match(data['schema']):
                schema_id = '/'.join(data['schema'].split('/')[:2])
            else:
                schema_id = data['schema']

            for schema in self.schema_versions_info:
                if schema_id == schema['id']:
                    self.schema = schema['schema'].schema
                    return
            self.schema = None

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
        validation_docs = []
        exceptions = []

        for document in self.documents:
            exc, debug_doc = self._validate_one(document)
            if exc:
                exceptions.append(exc)
                validation_docs.append(debug_doc)

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
            error = errors.InvalidDocumentFormat(
                detail=e.message, schema=e.schema,
                document_type=document['schema'])
            debug_doc = self._gen_debug_doc(base_schema.schema, raw_dict)
            return error, debug_doc

        doc_schema_type = self.SchemaType(raw_dict)
        if doc_schema_type.schema is None:
            error = errors.InvalidDocumentSchema(
                document_schema=document.get_schema(),
                schema_list=[
                    s['id'] for s in self.SchemaType.schema_versions_info])
            # Forcibly delete the schema to compel debugging information to
            # appear; this will trigger a schema is invalid debug message.
            del raw_dict['schema']
            debug_doc = self._gen_debug_doc(base_schema.schema, raw_dict)
            return error, debug_doc

        # Perform more detailed validation on each document depending on
        # its schema. If the document is abstract, validation errors are
        # ignored.
        try:
            jsonschema.validate(raw_dict, doc_schema_type.schema)
        except jsonschema.exceptions.ValidationError as e:
            if not document.is_abstract():
                raise errors.InvalidDocumentFormat(
                    detail=e.message, schema=e.schema,
                    document_type=document['schema'])
            else:
                LOG.info('Skipping schema validation for abstract '
                         'document: %s.', document)

    def _gen_debug_doc(self, schema, document):
        """Generate a debug document with schema deckhand/Debug/v1.

        The debug document servers two primary functions:

            1. If the document is completely malformed and fails schema
               validation completely, then the debug document will coerce
               the data into a "database-friendly" document (otherwise the
               data will fail the database's internal table validations).
            2. Debug information is stored alongside the document data itself.

        Libraries like ``warlock`` are not robust enough to generate sample
        data from a provided schema; these libraries expect that the user pass
        in kwargs that populate the ``warlock``-generated skeleton, which is
        then subjected to the ``schema``.

        Deckhand must therefore dynamically generate the kwargs such that
        ``warlock`` is able to successfully create an object for ``schema``.
        The object ``warlock`` creates will be a dictionary that contains
        the following form::

            {
                'schema': 'deckhand/Debug/v1',
                'metadata': {'name': '[1]', 'schema': '[2]'},
                'data': '[3]',
                'debug': {
                    'metadata': {
                        'name': (
                            '[1] This field has the wrong type. Given: int, '
                            'required: str.'),
                        'schema': (
                            '[2] This required field is missing or invalid.'),
                        'data': (
                            '[3] This required field is missing or invalid.')
                    },
                    'schema': (
                        '[uuid] This required field is missing or invalid.')
                } 
            }

        The above is a worst-case example that demonstrates a document that
        fails even basic schema validation. Each missing or invalid entry
        will have a reference (i.e. '[1]') which is in actuality a unique UUID.
        This UUID can be used for reference in the `debug` to determine the
        cause of failure. That is, if $.metadata.name has a wrong type then
        $.debug.metadata.name will convey that via a debug message.

        Fields that are present, valid and of the correct type are included
        in the generated document. Fields that are missing, invalid or of
        the incorrect type have a UUID reference and a corresponding section
        and explanation in $.debug.

        :returns: A document that adheres to the above format.
        """
        kwargs = self._gen_debug_doc_kwargs(schema, document, "$", {})
        DebugDocument = warlock.model_factory(schema)
        debug_document = DebugDocument(**kwargs)
        return debug_document

    def _gen_debug_doc_kwargs(self, schema, section, path, kwargs):
        """Recursively generate the kwargs needed by ``warlock`` to generate
        an object that adheres to the ``schema``.
        """
        if 'debug' in path:
            return kwargs

        if 'type' in schema:
            if 'properties' not in schema:
                # Determine if the required field is missing.
                field_val = utils.jsonpath_parse(section, path)
                missing = field_val is None

                # Determine if the field has the wrong type.
                required_type = schema['type']
                if not isinstance(required_type, list):
                    required_type = [required_type]
                given_type = type(field_val).__name__
                wrong_type = not any([self._compare_types(req_type, given_type)
                                     for req_type in required_type])

                # If the field is either missing or has the wrong type, then
                # generate debug information.
                if missing or wrong_type:
                    field_val, debug_uuid = self._gen_debug_value(path)
                    debug_msg, debug_path = self._gen_debug_message(
                        debug_uuid, path, missing, wrong_type,
                        given_type=given_type, required_type=required_type)
                    kwargs.update(
                        utils.jsonpath_replace(kwargs, debug_msg, debug_path))

                return utils.jsonpath_replace(kwargs, field_val, path)

        for prop in schema.get('properties', {}):
            jsonpath = path + "." + prop
            result = self._gen_debug_doc_kwargs(
                schema['properties'][prop], section, jsonpath, kwargs)
            if result:
                kwargs.update(result)

        return kwargs

    def _gen_debug_value(self, path):
        debug_uuid = uuidutils.generate_uuid()
        if path == "$.schema":
            return _DEBUG_SCHEMA, debug_uuid
        debug_msg = "[%s]" % debug_uuid
        return debug_msg, debug_uuid

    def _gen_debug_message(self, debug_uuid, path, missing, wrong_type,
                           **kwargs):
        if missing:
            msg = ("[%s] This required field is missing or invalid."
                   % debug_uuid)
        elif wrong_type:
            msg = ("[%s] This field has the wrong type. Given: %s, required: "
                   "%s." % (debug_uuid, kwargs['given_type'],
                            kwargs['required_type']))
        else:
            msg = "[%s] Unknown issue with this field." % debug_uuid
        return msg, "$.debug" + path[1:] 

    def _compare_types(self, expected, actual):
        if expected == 'object' and actual == 'dict':
            return True
        return expected.startswith(actual)
