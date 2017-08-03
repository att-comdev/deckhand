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

from deckhand.engine.schema import base_schema
from deckhand.engine.schema import v1_0
from deckhand import errors


class DocumentValidation(object):
    """Class for document validation logic for YAML files.

    This class is responsible for parsing, validating and retrieving secret
    values for values stored in the YAML file.

    :param data: YAML data that requires secrets to be validated, merged and
        consolidated.
    """

    def __init__(self, data):
        self._inner = data
        self.pre_validate_data()

    class SchemaVersion(object):
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
            """Constructor for ``SchemaVersion``.

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

    def pre_validate_data(self):
        """Pre-validate that the YAML file is correctly formatted.

        Validation is broken up into 2 stages:

            1) Validate that each document contains the basic bulding blocks
               needed: "schema", "metadata" and "data" using a "base" schema.
            2) Validate each specific document type (e.g. validation policy)
               using a more detailed schema.  
        """
        # Subject each document to basic validation to verify that each
        # major property is present (schema, metadata, data).
        try:
            jsonschema.validate(self._inner, base_schema.schema)
        except jsonschema.exceptions.ValidationError as e:
            raise errors.InvalidFormat(
                'The provided YAML file failed basic validation. '
                'Exception: %s. Schema: %s.' % (e.message, e.schema))

        doc_schema_version = self.SchemaVersion(self._inner)
        if doc_schema_version.schema is None:
            # TODO(fmontei): Raise a custom exception type once other PRs are
            # merged. 
            raise ValueError(
                "Could not determine the validation schema to validate the "
                "schema: %s." % self._inner['schema'])

        try:
            jsonschema.validate(self._inner, doc_schema_version.schema)
        except jsonschema.exceptions.ValidationError as e:
            raise errors.InvalidFormat(
                'The provided YAML file is invalid. Exception: %s. '
                'Schema: %s.' % (e.message, e.schema))
