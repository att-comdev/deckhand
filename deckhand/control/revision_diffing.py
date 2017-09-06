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
from oslo_log import log as logging

from deckhand.control import base as api_base
from deckhand.control.views import revision_tag as revision_tag_view
from deckhand.db.sqlalchemy import api as db_api
from deckhand import errors

LOG = logging.getLogger(__name__)


class RevisionDiffingResource(api_base.BaseResource):
    """API resource for realizing revision diffing."""

    def on_get(self, req, resp, revision_id, comparison_revision_id):
        if revision_id == '0':
            revision_id = 0
        if comparison_revision_id == '0':
            comparison_revision_id = 0

        try:
            resp_body = db_api.revision_diff_get(
                revision_id, comparison_revision_id)
        except (errors.RevisionNotFound) as e:
            raise falcon.HTTPNotFound(description=e.format_message())

        resp.status = falcon.HTTP_200
        resp.append_header('Content-Type', 'application/x-yaml')
        resp.body = self.to_yaml_body(resp_body)
