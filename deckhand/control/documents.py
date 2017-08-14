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

import falcon

from oslo_db import exception as db_exc
from oslo_log import log as logging

from deckhand.control import base as api_base
from deckhand.control import common
from deckhand.db.sqlalchemy import api as db_api
from deckhand.engine import document_validation
from deckhand import errors as deckhand_errors

LOG = logging.getLogger(__name__)


class DocumentsResource(api_base.BaseResource):
    """API resource for realizing CRUD endpoints for Documents."""

    @common.enforce_content_types(['application/x-yaml'])
    def on_post(self, req, resp):
        """Create a document. Accepts YAML data only."""
        documents = self.to_python_object(req)

        # All concrete documents in the payload must successfully pass their
        # JSON schema validations. Otherwise raise an error.
        try:
            validation_policies = document_validation.DocumentValidation(
                documents).validate_all()
        except (deckhand_errors.InvalidDocumentFormat,
                deckhand_errors.UnknownDocumentFormat) as e:
            raise falcon.HTTPBadRequest(title='Malformed document payload',
                                        description=repr(e))

        try:
            created_documents = db_api.documents_create(
                documents, validation_policies)
        except db_exc.DBDuplicateEntry as e:
            raise falcon.HTTPConflict(description=repr(e))
        except Exception as e:
            raise falcon.HTTPInternalServerError(description=repr(e))

        resp.status = falcon.HTTP_201
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(created_documents)
