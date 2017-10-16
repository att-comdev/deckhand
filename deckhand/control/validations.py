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

import yaml

import falcon

from deckhand.control import base as api_base
from deckhand.control.views import validation as validation_view
from deckhand.db.sqlalchemy import api as db_api
from deckhand import errors
from deckhand import policy


class ValidationsResource(api_base.BaseResource):
    """API resource for realizing validations endpoints."""

    view_builder = validation_view.ViewBuilder()

    @policy.authorize('deckhand:create_validation')
    def on_post(self, req, resp, revision_id, validation_name):
        validation_data = req.stream.read(req.content_length or 0)
        try:
            validation_data = yaml.safe_load(validation_data)
            
        except yaml.YAMLError as e:
            error_msg = ("Could not parse the validation into YAML data. "
                         "Details: %s." % e)
            LOG.error(error_msg)
            raise falcon.HTTPBadRequest(description=six.text_type(e))

        try:
            resp_body = db_api.validation_create(
                revision_id, validation_name, validation_data)
        except errors.RevisionNotFound as e:
            raise falcon.HTTPNotFound(description=e.format_message())

        resp.status = falcon.HTTP_201
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(self.view_builder.show(resp_body))

    def on_get(self, req, resp, revision_id, validation_name=None):
        """Returns list of existing revisions.

        Lists existing revisions and reports basic details including a summary
        of validation status for each `deckhand/ValidationPolicy` that is part
        of each revision.
        """
        if validation_name:
            self._show_validation(req, resp, revision_id, validation_name)
        else:
            self._list_validations(req, resp, revision_id)

    #@policy.authorize('deckhand:show_validation')
    def _show_validation(self, req, resp, revision_id, validation_name):
        try:
            validation = db_api.validation_get(revision_id, validation_name)
        except errors.RevisionNotFound as e:
            raise falcon.HTTPNotFound(description=e.format_message())

        resp_body = self.view_builder.show(validation)
        resp.status = falcon.HTTP_200
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(resp_body)

    #@policy.authorize('deckhand:list_validations')
    def _list_validations(self, req, resp, revision_id):
        validations = db_api.validation_get_all(revision_id)
        resp_body = self.view_builder.list(validations)

        resp.status = falcon.HTTP_200
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(resp_body)
