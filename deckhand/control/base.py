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

import uuid
import yaml

import falcon
from falcon import request
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class BaseResource(object):
    """Base resource class for implementing API resources."""

    def __init__(self):
        self.authorized_roles = []

    def on_options(self, req, resp):
        self_attrs = dir(self)
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH']
        allowed_methods = []

        for m in methods:
            if 'on_' + m.lower() in self_attrs:
                allowed_methods.append(m)

        resp.headers['Allow'] = ','.join(allowed_methods)
        resp.status = falcon.HTTP_200

    # For authorizing access at the Resource level. A Resource requiring
    # finer-grained authorization at the method or instance level must
    # implement that in the request handlers
    def authorize_roles(self, role_list):
        # TODO(fmontei): Update this when oslo.policy integration added.
        authorized = set(self.authorized_roles)
        applied = set(role_list)

        if authorized.isdisjoint(applied):
            return False
        else:
            return True

    def to_python_object(self, req):
        """Convert YAML payload into Python object.

        :returns: None if the payload is empty, else the Python object version
            of the YAML payload.
        :raises: falcon.HTTPBadRequest if the request payload could not be
            parsed into a Python object.
        """
        if req.content_length is None or req.content_length == 0:
            return None

        raw_body = req.stream.read(req.content_length or 0)

        if not raw_body:
            return None

        try:
            yaml_body = [
                x for x in yaml.safe_load_all(raw_body.decode('utf-8'))]
            return yaml_body
        except yaml.YAMLError as e:
            error_msg = ("Could not parse the request body into YAML data."
                         " Details: %s." % e)
            LOG.error(error_msg)
            raise falcon.HTTPBadRequest(title='Malformed document payload',
                                        description='msg')

    def to_yaml_body(self, dict_body):
        """Converts JSON body into YAML response body.

        :dict_body: response body to be converted to YAML.
        :returns: YAML encoding of `dict_body`.
        """
        if isinstance(dict_body, dict):
            return yaml.safe_dump(dict_body)
        elif isinstance(dict_body, list):
            return yaml.safe_dump_all(dict_body)
        raise TypeError('Unrecognized dict_body type when converting response '
                        'body to YAML format.')


class DeckhandRequestContext(object):
    # TODO(fmontei): Update this when oslo.policy integration added.

    def __init__(self):
        self.user = None
        self.roles = []
        self.request_id = str(uuid.uuid4())

    def set_user(self, user):
        self.user = user

    def add_role(self, role):
        self.roles.append(role)

    def add_roles(self, roles):
        self.roles.extend(roles)

    def remove_role(self, role):
        if role in self.roles:
            self.roles.remove(role)


class DeckhandRequest(request.Request):
    context_type = DeckhandRequestContext
