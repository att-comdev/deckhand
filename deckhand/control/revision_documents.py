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

import falcon
from oslo_log import log as logging
import six

from deckhand.control import base as api_base
from deckhand.control import common
from deckhand.control.views import document as document_view
from deckhand.db.sqlalchemy import api as db_api
from deckhand.engine import document_validation
from deckhand.engine import layering
from deckhand import errors
from deckhand import policy
from deckhand import types

LOG = logging.getLogger(__name__)


class RevisionDocumentsResource(api_base.BaseResource):
    """API resource for realizing revision documents endpoint."""

    view_builder = document_view.ViewBuilder()

    @policy.authorize('deckhand:list_cleartext_documents')
    @common.sanitize_params([
        'schema', 'metadata.name', 'metadata.layeringDefinition.abstract',
        'metadata.layeringDefinition.layer', 'metadata.label',
        'status.bucket'])
    def on_get(self, req, resp, sanitized_params, revision_id):
        """Returns all documents for a `revision_id`.

        Returns a multi-document YAML response containing all the documents
        matching the filters specified via query string parameters. Returned
        documents will be as originally posted with no substitutions or
        layering applied.
        """
        include_encrypted = policy.conditional_authorize(
            'deckhand:list_encrypted_documents', req.context, do_raise=False)

        filters = sanitized_params.copy()
        filters['metadata.storagePolicy'] = ['cleartext']
        if include_encrypted:
            filters['metadata.storagePolicy'].append('encrypted')
        filters['deleted'] = False  # Never return deleted documents to user.

        try:
            documents = db_api.revision_get_documents(
                revision_id, **filters)
        except errors.RevisionNotFound as e:
            LOG.exception(six.text_type(e))
            raise falcon.HTTPNotFound(description=e.format_message())

        resp.status = falcon.HTTP_200
        resp.body = self.view_builder.list(documents)


class RenderedDocumentsResource(api_base.BaseResource):
    """API resource for realizing rendered documents endpoint.

    Rendered documents are also revision documents, but unlike revision
    documents, they are finalized documents, having undergone secret
    substitution and document layering.

    Returns a multi-document YAML response containing all the documents
    matching the filters specified via query string parameters. Returned
    documents will have secrets substituted into them and be layered with
    other documents in the revision, in accordance with the ``LayeringPolicy``
    that currently exists in the system.
    """

    view_builder = document_view.ViewBuilder()

    @policy.authorize('deckhand:list_cleartext_documents')
    @common.sanitize_params([
        'schema', 'metadata.name', 'metadata.label'])
    def on_get(self, req, resp, sanitized_params, revision_id):
        include_encrypted = policy.conditional_authorize(
            'deckhand:list_encrypted_documents', req.context, do_raise=False)

        filters = sanitized_params.copy()
        filters['metadata.layeringDefinition.abstract'] = False
        filters['metadata.storagePolicy'] = ['cleartext']
        filters['deleted'] = False  # Never return deleted documents to user.
        if include_encrypted:
            filters['metadata.storagePolicy'].append('encrypted')

        try:
            documents = db_api.revision_get_documents(
                revision_id, **filters)
        except errors.RevisionNotFound as e:
            LOG.exception(six.text_type(e))
            raise falcon.HTTPNotFound(description=e.format_message())

        layering_policy = self._extract_layering_policy(documents)
        if layering_policy is None:
            LOG.error('No layering policy found so could not render '
                      'the documents for revision %s.', revision_id)
            resp.status = falcon.HTTP_409
            resp.body = self.view_builder.list(documents)
        else:
            document_layering = layering.DocumentLayering(layering_policy,
                                                          documents)
            rendered_documents = document_layering.render()

            resp.status = falcon.HTTP_200
            resp.body = self.view_builder.list(rendered_documents)
            self._post_validate(rendered_documents)

    def _extract_layering_policy(self, documents):
        for doc in copy.copy(documents):
            if doc['schema'].startswith(types.LAYERING_POLICY_SCHEMA):
                layering_policy = doc
                documents.remove(doc)
                return layering_policy
        return None

    def _post_validate(self, rendered_documents):
        # Perform schema validation post-rendering to ensure that rendering
        # and substitution didn't break anything.
        doc_validator = document_validation.DocumentValidation(
            rendered_documents)
        try:
            doc_validator.validate_all()
        except (errors.InvalidDocumentFormat,
                errors.InvalidDocumentSchema) as e:
            LOG.error('Failed to post-validate rendered documents.')
            LOG.exception(e.format_message())
            raise falcon.HTTPInternalServerError(
                description=e.format_message())
