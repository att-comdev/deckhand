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
import copy
import re

import jsonschema
from oslo_log import log as logging
import six

from deckhand.engine.schema import base_schema
from deckhand.engine.schema import v1_0
from deckhand import errors
from deckhand import types

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseValidator(object):
    """Abstract base validator.

    Sub-classes should override this to implement schema-specific document
    validation.
    """

    @abc.abstractmethod
    def validate(self, document):
        """Validate whether ``document`` passes schema validation."""


class GenericValidator(BaseValidator):

    def validate(self, document):
        """Validates whether ``document``passes basic schema validation.

        Sanity-checks each document for mandatory keys like "metadata" and
        "schema".

        Applies even to abstract documents, as they must be consumed by
        concrete documents, so basic formatting is mandatory.

        Failure to pass this results in an error.

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
            LOG.error('Document failed top-level schema validation. Details: '
                      '%s.', e.message)
            # NOTE(fmontei): Raise here because if the document fails sanity
            # check then this is a critical failure.
            raise errors.InvalidDocumentFormat(detail=e.message,
                                               schema=e.schema)


class SchemaValidator(BaseValidator):

        # TODO(fmontei): Make this work with different API versions, if needed.
        _schema_versions_info = {
            'deckhand/CertificateKey': v1_0.certificate_key_schema,
            'deckhand/Certificate': v1_0.certificate_schema,
            'deckhand/DataSchema': v1_0.data_schema_schema,
            'deckhand/LayeringPolicy': v1_0.layering_policy_schema,
            'deckhand/Passphrase': v1_0.passphrase_schema,
            'deckhand/ValidationPolicy': v1_0.validation_policy_schema,
            # Represents a generic document schema.
            '*': v1_0.document_schema.schema
        }

        _schema_re = re.compile(
            '^([A-Za-z]+\/[A-Za-z]+\/v[1]{1}(\.[0]{1}){0,1})$')

        def __init__(self, data_schemas):
            super(SchemaValidator, self).__init__()
            self.data_schemas = data_schemas
            self.registered_schemas = self._register_all_schemas()

        def _register_all_schemas(self):
            """Dynamically detect schemas for document validation that have
            been registered by external services via ``DataSchema`` documents.

            :returns: All schemas contained in ``_schema_versions_info`` in
                addition to registered ``DataSchema`` documents found in the
                DB.
            """

            registered_schemas = copy.copy(
                SchemaValidator._schema_versions_info)

            for data_schema in self.data_schemas:
                try:
                    if SchemaValidator._schema_re.match(
                            data_schema['metadata']['name']):
                        schema_prefix = '/'.join(
                            data_schema['metadata']['name'].split('/')[:2])
                    else:
                        schema_prefix = data_schema['metadata']['name']

                    validation_schema = copy.deepcopy(
                        SchemaValidator._schema_versions_info['*'])
                    validation_schema['properties']['data'] = (
                        data_schema['data'])
                except (KeyError, TypeError):
                    continue

                # Coerce a dictionary-formatted document into an object so it's
                # consistent with the other module-level schemas contained in
                # ``SchemaValidator._schema_versions_info``.
                class Schema(object):
                    schema = validation_schema
                registered_schemas.setdefault(schema_prefix, Schema())

            return registered_schemas

        def _get_schemas(self, document):
            """Retrieve the relevant schemas based on the document's
            ``schema``.

            :param dict doc: The document used for finding the correct schema
                to validate it based on its ``schema``.
            :returns: A schema to be used by ``jsonschema`` for document
                validation.
            :rtype: dict
            """

            if SchemaValidator._schema_re.match(document['schema']):
                target_schema_prefix = (
                    '/'.join(document['schema'].split('/')[:2]))
            else:
                target_schema_prefix = document['schema']

            matching_schemas = []
            for schema_prefix, schema in self.registered_schemas.items():
                # Can't use `startswith` below to avoid namespace false
                # positives like `CertificateKey` and `Certificate`.
                if target_schema_prefix == schema_prefix:
                    if schema not in matching_schemas:
                        matching_schemas.append(schema)

            return matching_schemas

        def validate(self, document):
            """Perform more detailed validation on each document depending on
            its schema. If the document is abstract, then no validation is
            performed.

            Does not apply to abstract documents.

            :raises RuntimeError: If the Deckhand schema itself is invalid.
            :raises errors.InvalidDocumentFormat: If Deckhand could not find
                schemas used to validate the document further.
            :returns: An error message following schema validation failure.
                Else None.
            :rtype: str
            """
            try:
                is_abstract = document['metadata']['layeringDefinition'][
                    'abstract']
            except KeyError:
                is_abstract = False

            if is_abstract is True:
                LOG.info('Skipping schema validation for abstract '
                         'document: %s.', document)
                return

            schemas_to_use = self._get_schemas(document)
            if not schemas_to_use:
                LOG.debug('Document schema %s not recognized.',
                          document['schema'])
                # Raise here because if Deckhand cannot even determine which
                # schemas to use for further validation, then no meaningful
                # validation can be performed, so this is a critical failure.
                raise errors.InvalidDocumentSchema(
                    document_schema=document['schema'],
                    schema_list=[
                        s for s in self.registered_schemas if s != '*'])

            for schema_to_use in schemas_to_use:
                try:
                    schema_validator = schema_to_use.schema
                    jsonschema.validate(document, schema_validator)
                except jsonschema.exceptions.SchemaError as e:
                    raise RuntimeError(
                        'Unknown error occurred while attempting to use'
                        'Deckhand schema. Details: %s.' % six.text_type(e))
                except jsonschema.exceptions.ValidationError as e:
                    LOG.error(
                        'Document failed schema validation for schema %s.'
                        'Details: %s.', document['schema'], e.message)
                    return e.message


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

        data_schemas = []
        all_other_documents = []

        if not isinstance(documents, (list, tuple)):
            documents = [documents]

        for document in documents:
            if not isinstance(document, dict):
                continue
            _document = copy.deepcopy(document)
            # FIXME(fmontei): Remove extraneous top-level keys so that fully
            # rendered documents pass schema validation. This should be handled
            # more carefully later.
            for key in document:
                if key not in ('metadata', 'schema', 'data'):
                    _document.pop(key)
            if _document.get('schema', '').startswith(
                    types.DATA_SCHEMA_SCHEMA):
                data_schemas.append(_document)
            else:
                all_other_documents.append(_document)

        self.documents = data_schemas + all_other_documents

        # NOTE(fmontei): The order of the validators is important. The
        # ``GenericValidator`` must come first.
        self._validators = [
            GenericValidator(),
            SchemaValidator(data_schemas)
        ]

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

        for validator in self._validators:
            error_message = validator.validate(document)
            if error_message:
                result['errors'].append({
                    'schema': document['schema'],
                    'name': document['metadata']['name'],
                    'message': error_message
                })

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
        :rtype: `func`:list[dict]
        :raises errors.InvalidDocumentFormat: If the document failed schema
            validation and the failure is deemed critical.
        :raises errors.InvalidDocumentSchema: If no JSON schema for could be
            found for executing document validation.
        :raises RuntimeError: If a Deckhand schema itself is invalid.
        """
        validation_results = []
        for document in self.documents:
            result = self._validate_one(document)
            validation_results.append(result)

        validations = self._format_validation_results(validation_results)
        return validations
