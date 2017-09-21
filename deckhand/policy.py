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

import functools

from oslo_config import cfg
from oslo_log import log as logging
from oslo_policy import policy
from oslo_utils import excutils

from deckhand import errors
from deckhand import policies

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def enforce(action):

    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            context = args[1].context
            policy_enforcer = args[1].policy_enforcer
            credentials = context.to_policy_values()
            exc = errors.PolicyNotAuthorized

            try:
                policy_enforcer.enforce(
                    action, {}, context.to_dict(), do_raise=True, exc=exc,
                    action=action)
            except policy.PolicyNotRegistered:
                with excutils.save_and_reraise_exception():
                    LOG.exception('Policy not registered.')
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.debug(
                        'Policy check for %(action)s failed with credentials '
                        '%(credentials)s',
                        {'action': action, 'credentials': credentials})

            return func(*args, **kwargs)
        return handler

    return decorator


def register_rules(enforcer):
    enforcer.register_defaults(policies.list_rules())
