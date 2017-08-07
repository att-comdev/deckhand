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

from deckhand.control import base as api_base
from deckhand.control.views import revision_tag as revision_tag_view
from deckhand.db.sqlalchemy import api as db_api
from deckhand import errors


class RevisionTagsResource(api_base.BaseResource):
    """API resource for realizing CRUD for revision tags."""

    def on_put(self, req, resp, revision_id, tag=None):
        """Creates a tag for a revision or replaces all tags for a revision."""
        if tag:
            self._create_tag(req, resp, revision_id, tag)
        else:
            self._replace_all_tags(req, resp, revision_id)

    def _create_tag(self, req, resp, revision_id, tag):
        """Creates a revision tag."""
        try:
            resp_tag = db_api.revision_tag_create(revision_id, tag)
        except errors.RevisionNotFound as e:
            return self.return_error(resp, falcon.HTTP_404, message=e)

        resp_body = revision_tag_view.ViewBuilder().show(resp_tag)
        resp.status = falcon.HTTP_201
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(resp_body)

    def _replace_all_tags(self, req, resp, revision_id):
        """Replaces all tags for a revision."""
        tags = req.params.get('tags')

        try:
            resp_tags = db_api.revision_tag_replace_all(revision_id, tags)
        except errors.RevisionNotFound as e:
            return self.return_error(resp, falcon.HTTP_404, message=e)

        resp_body = revision_tag_view.ViewBuilder().list(resp_tags)
        resp.status = falcon.HTTP_200
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(resp_body)

    def on_get(self, req, resp, revision_id, tag=None):
        """Creates a tag for a revision or replaces all tags for a revision."""
        if tag:
            self._check_tag_existence(req, resp, revision_id, tag)
        else:
            self._list_all_tags(req, resp, revision_id)

    def _check_tag_existence(self, req, resp, revision_id, tag):
        """Creates a revision tag."""
        try:
            db_api.revision_tag_check(revision_id, tag)
        except (errors.RevisionNotFound,
                errors.RevisionTagNotFound) as e:
            return self.return_error(resp, falcon.HTTP_404, message=e)

        resp.status = falcon.HTTP_204

    def _list_all_tags(self, req, resp, revision_id):
        """Replaces all tags for a revision."""
        try:
            revision_tags = db_api.revision_tag_get_all(revision_id)
        except errors.RevisionNotFound as e:
            return self.return_error(resp, falcon.HTTP_404, message=e)

        resp_body = revision_tag_view.ViewBuilder().list(revision_tags)
        resp.status = falcon.HTTP_200
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(resp_body)

    def on_delete(self, req, resp, revision_id, tag=None):
        """Creates a tag for a revision or replaces all tags for a revision."""
        if tag:
            self._delete_tag(req, resp, revision_id, tag)
        else:
            self._delete_all_tags(req, resp, revision_id)

    def _delete_tag(self, req, resp, revision_id, tag):
        """Creates a revision tag."""
        try:
            db_api.revision_tag_delete(revision_id, tag)
        except (errors.RevisionNotFound,
                errors.RevisionTagNotFound) as e:
            return self.return_error(resp, falcon.HTTP_404, message=e)

        resp.status = falcon.HTTP_204

    def _delete_all_tags(self, req, resp, revision_id):
        """Replaces all tags for a revision."""
        try:
            db_api.revision_tag_delete_all(revision_id)
        except errors.RevisionNotFound as e:
            return self.return_error(resp, falcon.HTTP_404, message=e)

        resp.status = falcon.HTTP_204
