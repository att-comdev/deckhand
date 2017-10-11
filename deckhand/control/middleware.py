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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils as json

import deckhand.context
from deckhand import errors

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class ContextMiddleware(object):

    def process_request(self, req, resp):
        """Convert authentication information into a request context

        Generate a glance.context.RequestContext object from the available
        authentication headers and store on the 'context' attribute
        of the req object.

        :param req: wsgi request object that will be given the context object
        :raises: falcon.HTTPUnauthorized: when value of the
            X-Identity-Status header is not 'Confirmed' and anonymous access
            is disallowed
        """
        if req.headers.get('X-IDENTITY-STATUS') == 'Confirmed':
            req.context = deckhand.context.RequestContext.from_environ(req.env)
        elif CONF.allow_anonymous_access:
            req.context = deckhand.context.get_context()
        else:
            raise falcon.HTTPUnauthorized('foobar')


class HookableMiddlewareMixin(object):
    """Provides methods to extract before and after hooks from WSGI Middleware
    Prior to falcon 0.2.0b1, it's necessary to provide falcon with middleware
    as "hook" functions that are either invoked before (to process requests)
    or after (to process responses) the API endpoint code runs.
    This mixin allows the process_request and process_response methods from a
    typical WSGI middleware object to be extracted for use as these hooks, with
    the appropriate method signatures.
    """

    def as_before_hook(self):
        """Extract process_request method as "before" hook
        :return: before hook function
        """

        # Need to wrap this up in a closure because the parameter counts
        # differ
        def before_hook(req, resp, params=None):
            return self.process_request(req, resp)

        try:
            return before_hook
        except AttributeError as ex:
            # No such method, we presume.
            message_template = ("Failed to get before hook from middleware "
                                "{0} - {1}")
            message = message_template.format(self.__name__, ex.message)
            LOG.error(message)
            raise errors.DeckhandException(message)

    def as_after_hook(self):
        """Extract process_response method as "after" hook
        :return: after hook function
        """

        # Need to wrap this up in a closure because the parameter counts
        # differ
        def after_hook(req, resp, resource=None):
            return self.process_response(req, resp, resource)

        try:
            return after_hook
        except AttributeError as ex:
            # No such method, we presume.
            message_template = ("Failed to get after hook from middleware "
                                "{0} - {1}")
            message = message_template.format(self.__name__, ex.message)
            LOG.error(message)
            raise errors.DeckhandException(message)


class JSONTranslator(HookableMiddlewareMixin, object):

    def process_response(self, req, resp, resource):
        if not hasattr(resp, 'body'):
            return
        if isinstance(resp.data, dict):
            resp.data = json.dumps(resp.data)

        if isinstance(resp.body, dict):
            resp.body = json.dumps(resp.body)
