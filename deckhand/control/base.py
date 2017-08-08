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
from oslo_context import context
from oslo_log import log as logging
from oslo_serialization import jsonutils as json
import six

from deckhand import errors

LOG = logging.getLogger(__name__)


class BaseResource(object):
    """Base resource class for implementing API resources."""

    def on_options(self, req, resp):
        self_attrs = dir(self)
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH']
        allowed_methods = []

        for m in methods:
            if 'on_' + m.lower() in self_attrs:
                allowed_methods.append(m)

        resp.headers['Allow'] = ','.join(allowed_methods)
        resp.status = falcon.HTTP_200

    def return_error(self, resp, status_code, message="", retry=False):
        resp.body = json.dumps(
            {'type': 'error', 'message': six.text_type(message),
             'retry': retry})
        resp.status = status_code

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


class DeckhandRequestContext(context.RequestContext):
    """Stores information about the security context.

    Stores how the user accesses the system, as well as additional request
    information.
    """

    def __init__(self, service_catalog=None, **kwargs):
        super(RequestContext, self).__init__(**kwargs)
        self.service_catalog = service_catalog

    def to_dict(self):
        d = super(RequestContext, self).to_dict()
        d.update({
            'roles': self.roles,
            'service_catalog': self.service_catalog,
        })
        return d

    def to_policy_values(self):
        pdict = super(RequestContext, self).to_policy_values()
        pdict['user'] = self.user
        pdict['tenant'] = self.tenant
        return pdict

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def get_admin_context(show_deleted=False):
    """Create an administrator context."""
    return RequestContext(auth_token=None,
                          tenant=None,
                          is_admin=True,
                          show_deleted=show_deleted,
                          overwrite=False)


class DeckhandRequest(falcon.request.Request):
    context_type = DeckhandRequestContext
