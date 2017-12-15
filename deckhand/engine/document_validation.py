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

import abc
import re

import jsonschema
from oslo_log import log as logging
import six

from deckhand.db.sqlalchemy import api as db_api
from deckhand.engine.schema import base_schema
from deckhand.engine.schema import v1_0
from deckhand import errors
from deckhand import types
from deckhand import utils

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseValidator(object):
    """Abstract base validator.

    Sub-classes should override this to implement schema-specific document
    validation.
    """

    _supported_versions = ('v1',)
    _schema_re = re.compile(r'^[a-zA-Z]+\/[a-zA-Z]+\/v[1](.0)?$')

    @abc.abstractmethod
    def matches(self, document):
        """Returns whether the document's schema applies to the ``Validator``.
        """

    @abc.abstractmethod
    def validate(self, document):
        """Validate whether ``document`` passes schema validation."""


class GenericValidator(BaseValidator):
    """Validator used for validating all documents, regardless whether concrete
    or abstract, or what version its schema is.
    """

    def matches(self, document):
        return True

    def validate(self, document):
        """Validate ``document``against basic schema validation.

        Sanity-checks each document for mandatory keys like "metadata" and
        "schema".

        Applies even to abstract documents, as they must be consumed by
        concrete documents, so basic formatting is mandatory.

        Failure to pass this check results in an error.

        :raises RuntimeError: If the Deckhand schema itself is invalid.
        :raises errors.InvalidDocumentFormat: If the document failed schema
            validation.
        :returns: None

        """
        try:
            jsonschema.validate(document, base_schema.schema)
        except jsonschema.exceptions.SchemaError as e:
            raise RuntimeError(
                'Unknown error occurred while attempting to use Deckhand '
                'schema. Details: %s.' % six.text_type(e))
        except jsonschema.exceptions.ValidationError as e:
            LOG.error('Document failed sanity-check validation. Details: %s.',
                      e.message)
            raise errors.InvalidDocumentFormat(detail=e.message,
                                               schema=e.schema)


class SchemaValidator(BaseValidator):
    """Validator for validating built-in document kinds."""

    _schema_map = {
        'v1': {
            'deckhand/CertificateKey': v1_0.certificate_key_schema,
            'deckhand/Certificate': v1_0.certificate_schema,
            'deckhand/DataSchema': v1_0.data_schema_schema,
            'deckhand/LayeringPolicy': v1_0.layering_policy_schema,
            'deckhand/Passphrase': v1_0.passphrase_schema,
            'deckhand/ValidationPolicy': v1_0.validation_policy_schema,
        }
    }

    # Represents a generic document schema.
    _fallback_schema = v1_0.document_schema

    def _get_schemas(self, document):
        """Retrieve the relevant schemas based on the document's
        ``schema``.

        :param dict doc: The document used for finding the correct schema
            to validate it based on its ``schema``.
        :returns: A schema to be used by ``jsonschema`` for document
            validation.
        :rtype: dict

        """
        schema_prefix, schema_version = get_schema_parts(document)
        matching_schemas = []
        relevant_schemas = self._schema_map[schema_version]
        for candidae_schema_prefix, schema in relevant_schemas.items():
            if candidae_schema_prefix == schema_prefix:
                if schema not in matching_schemas:
                    matching_schemas.append(schema)
        return matching_schemas

    def matches(self, document):
        if is_abstract(document) is True:
            LOG.info('Skipping schema validation for abstract document [%s]: '
                     '%s.', document['schema'], document['metadata']['name'])
            return False
        _, schema_version = get_schema_parts(document)
        if schema_version not in self._supported_versions:
            LOG.debug('Unsupported schema version for document [%s]: %s.',
                      document['schema'], document['metadata']['name'])
            return False
        return True

    def validate(self, document):
        """Validate ``document`` against built-in ``schema``-specific schemas.

        Does not apply to abstract documents.

        :raises RuntimeError: If the Deckhand schema itself is invalid.
        :raises errors.InvalidDocumentFormat: If Deckhand could not find
            schemas used to validate the document further.
        :returns: Error messages following schema validation failure.
        :rtype: generator[str]

        """
        schemas_to_use = self._get_schemas(document)
        if not schemas_to_use:
            LOG.debug('Document schema %s not recognized. Using "fallback" '
                      'schema.', document['schema'])
            schemas_to_use = [SchemaValidator._fallback_schema]

        for schema_to_use in schemas_to_use:
            try:
                schema_validator = schema_to_use.schema
                jsonschema.validate(document, schema_validator)
            except jsonschema.exceptions.SchemaError as e:
                LOG.exception(six.text_type(e))
                raise RuntimeError(
                    'Unknown error occurred while attempting to use'
                    'Deckhand schema. Details: %s.' % six.text_type(e))
            except jsonschema.exceptions.ValidationError as e:
                LOG.error(
                    'Document failed schema validation for schema %s. '
                    'Details: %s.', document['schema'], e.message)
                yield e.message


class DataSchemaValidator(BaseValidator):
    """Validator for validating ``DataSchema`` documents."""

    def __init__(self, data_schemas):
        super(DataSchemaValidator, self).__init__()
        self._schema_map = self._build_schema_map(data_schemas)

    def _build_schema_map(self, data_schemas):
        schema_map = {k: {} for k in self._supported_versions}

        for data_schema in data_schemas:
            # Ensure that each `DataSchema` document has required properties
            # before they themselves can be used to validate other documents.
            if 'name' not in data_schema.get('metadata', {}):
                continue
            if self._schema_re.match(data_schema['metadata']['name']) is None:
                continue
            if 'data' not in data_schema:
                continue
            schema_prefix, schema_version = get_schema_parts(data_schema,
                                                             'metadata.name')

            class Schema(object):
                schema = data_schema['data']

            schema_map[schema_version].setdefault(schema_prefix, Schema())

        return schema_map

    def _get_schemas(self, document):
        """Retrieve the relevant schemas based on the document's
        ``schema``.

        :param dict document: The document used for finding the correct schemas
            to validate it based on its ``schema``.
        :returns: A list of schemas to be used by ``jsonschema`` for document
            validation.
        :rtype: :func:`list[dict]`

        """
        schema_prefix, schema_version = get_schema_parts(document)
        matching_schemas = []
        relevant_schemas = self._schema_map[schema_version]
        for candidate_schema_prefix, schema in relevant_schemas.items():
            if candidate_schema_prefix == schema_prefix:
                if schema not in matching_schemas:
                    matching_schemas.append(schema)
        return matching_schemas

    def matches(self, document):
        if is_abstract(document) is True:
            LOG.info('Skipping schema validation for abstract document [%s]: '
                     '%s.', document['schema'], document['metadata']['name'])
            return False
        schema_prefix, schema_version = get_schema_parts(document)
        if schema_version not in self._supported_versions:
            LOG.debug('Unsupported schema version for document [%s]: %s.',
                      document['schema'], document['metadata']['name'])
            return False
        return schema_prefix in self._schema_map[schema_version]

    def validate(self, document):
        """Validate ``document`` against each matching ``DataSchema``s.

        Does not apply to abstract documents.

        :raises RuntimeError: If the Deckhand schema itself is invalid.
        :raises errors.InvalidDocumentFormat: If Deckhand could not find
            schemas used to validate the document further.
        :returns: Error messages following schema validation failure.
        :rtype: generator[str]

        """
        schemas_to_use = self._get_schemas(document)
        for schema_to_use in schemas_to_use:
            try:
                schema_validator = schema_to_use.schema
                jsonschema.validate(document.get('data'), schema_validator)
            except jsonschema.exceptions.SchemaError as e:
                LOG.exception(six.text_type(e))
                raise RuntimeError(
                    'Unknown error occurred while attempting to use'
                    'Deckhand schema. Details: %s.' % six.text_type(e))
            except jsonschema.exceptions.ValidationError as e:
                LOG.error(
                    'Document failed schema validation for schema %s. '
                    'Details: %s.', document['schema'], e.message)
                yield e.message


class DocumentValidation(object):

    def __init__(self, documents):
        """Class for document validation logic for documents.

        This class is responsible for validating documents according to their
        schema.

        ``DataSchema`` documents must be validated first, as they are in turn
        used to validate other documents.

        :param documents: Documents to be validated.
        :type documents: :func:`list[dict]`

        """

        self.documents = []
        data_schemas = db_api.revision_get_documents(
            schema=types.DATA_SCHEMA_SCHEMA, deleted=False)

        if not isinstance(documents, (list, tuple)):
            documents = [documents]

        for document in documents:
            if document.get('schema', '').startswith(types.DATA_SCHEMA_SCHEMA):
                data_schemas.append(document)
            self.documents.append(document)

        # NOTE(fmontei): The order of the validators is important. The
        # ``GenericValidator`` must come first.
        self._validators = [
            GenericValidator(),
            SchemaValidator(),
            DataSchemaValidator(data_schemas)
        ]

    def _get_supported_schema_list(self):
        schema_list = []
        for validator in self._validators[1:]:
            for schema_version, schema_map in validator._schema_map.items():
                for schema_prefix in schema_map:
                    schema_list.append(schema_prefix + '/' + schema_version)
        return schema_list

    def _format_validation_results(self, results):
        """Format the validation result to be compatible with database
        formatting.

        :results: The validation results generated during document validation.
        :type results: list[dict]
        :returns: List of formatted validation results.
        :rtype: `func`:list[dict]

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
        result = {'errors': []}
        # Flag for validating whether a document is validated at least once.
        # Ignores the ``GenericValidator`` validator and defaults to True if
        # the document is abstract because abstract documents need not be
        # validated.
        executed_at_least_one_validation = is_abstract(document)

        for validator in self._validators:
            if validator.matches(document):
                error_messages = validator.validate(document)
                if error_messages:
                    for error_message in error_messages:
                        result['errors'].append({
                            'schema': document['schema'],
                            'name': document['metadata']['name'],
                            'message': error_message
                        })
                if not isinstance(validator, GenericValidator):
                    executed_at_least_one_validation = True

        if not executed_at_least_one_validation:
            raise errors.InvalidDocumentSchema(
                schema=document.get('schema', 'N/A'),
                schema_list=self._get_supported_schema_list())

        if result['errors']:
            result.setdefault('status', 'failure')
        else:
            result.setdefault('status', 'success')

        return result

    def validate_all(self):
        """Pre-validate that all documents are correctly formatted.

        All concrete documents in the revision must successfully pass their
        JSON schema validations. The result of the validation is stored under
        the "deckhand-document-schema-validation" validation namespace for
        a document revision.

        All abstract documents must themselves be sanity-checked.

        Validation is broken up into 3 stages:

            1) Validate that each document contains the basic bulding blocks
               needed: i.e. ``schema`` and ``metadata`` using a "base" schema.
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

            3) Execute ``DataSchema`` validations if applicable.

        :returns: A list of validations (one for each document validated).
        :rtype: `func`:list[dict]
        :raises errors.InvalidDocumentFormat: If the document failed schema
            validation and the failure is deemed critical.
        :raises errors.InvalidDocumentSchema: If no JSON schema for could be
            found for executing document validation.
        :raises RuntimeError: If a Deckhand schema itself is invalid.

        """

        validation_results = []

        for document in self.documents:
            # NOTE(fmontei): Since ``DataSchema`` documents created in previous
            # revisions are retrieved and combined with new ``DataSchema``
            # documents, we only want to create a validation result in the DB
            # for the new documents. One way to do this is to check whether the
            # document contains the 'id' key which is only assigned by the DB.
            requires_validation = 'id' not in document

            if requires_validation:
                result = self._validate_one(document)
                validation_results.append(result)

        validations = self._format_validation_results(validation_results)
        return validations


def is_abstract(document):
    try:
        is_abstract = document['metadata']['layeringDefinition'][
            'abstract']
    except KeyError:
        return False
    return is_abstract


def get_schema_parts(document, schema_key='schema'):
    schema_parts = utils.jsonpath_parse(document, schema_key).split('/')
    schema_prefix = '/'.join(schema_parts[:2])
    schema_version = schema_parts[2]
    if schema_version.endswith('.0'):
        schema_version = schema_version[:-2]
    return schema_prefix, schema_version
