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

import deckhand.context


context_opts = [
    cfg.BoolOpt('allow_anonymous_access', default=False,
                help="""
Allow limited access to unauthenticated users.

Assign a boolean to determine API access for unathenticated
users. When set to False, the API cannot be accessed by
unauthenticated users. When set to True, unauthenticated users can
access the API with read-only privileges. This however only applies
when using ContextMiddleware.

Possible values:
    * True
    * False
"""),
]


CONF = cfg.CONF
CONF.register_opts(context_opts)


class AuthMiddleware(object):

    def process_request(self, req, resp):
        ctx = req.context

        auth_status = req.get_header(
            'X-SERVICE-IDENTITY-STATUS')  # Values include Confirmed or Invalid
        service = True

        if auth_status is None:
            auth_status = req.get_header('X-IDENTITY-STATUS')
            service = False

        if auth_status == 'Confirmed':
            # User Identity, unique within owning domain
            ctx.user = req.get_header(
                'X-SERVICE-USER-NAME') if service else req.get_header(
                    'X-USER-NAME')
            # Identity-service managed unique identifier
            ctx.user_id = req.get_header(
                'X-SERVICE-USER-ID') if service else req.get_header(
                    'X-USER-ID')
            # Identity service managed unique identifier of owning domain of
            # user name
            ctx.user_domain_id = req.get_header(
                'X-SERVICE-USER-DOMAIN-ID') if service else req.get_header(
                    'X-USER-DOMAIN-ID')
            # Identity service managed unique identifier
            ctx.project_id = req.get_header(
                'X-SERVICE-PROJECT-ID') if service else req.get_header(
                    'X-PROJECT-ID')
            # Name of owning domain of project
            ctx.project_domain_id = req.get_header(
                'X-SERVICE-PROJECT-DOMAIN-ID') if service else req.get_header(
                    'X-PROJECT-DOMAIN-NAME')
            if service:
                # Comma-delimited list of case-sensitive role names
                ctx.add_roles(req.get_header('X-SERVICE-ROLES').split(','))
            else:
                ctx.add_roles(req.get_header('X-ROLES').split(','))

            if req.get_header('X-IS-ADMIN-PROJECT') == 'True':
                ctx.is_admin_project = True
            else:
                ctx.is_admin_project = False
        elif CONF.allow_anonymous_access:
            req.context = self._get_anonymous_context()
        else:
            raise falcon.HTTPUnauthorized()

    def _get_anonymous_context(self):
        kwargs = {
            'user': None,
            'project': None,
            'roles': [],
            'is_admin': False,
            'read_only': True,
        }
        return deckhand.context.RequestContext(**kwargs)
