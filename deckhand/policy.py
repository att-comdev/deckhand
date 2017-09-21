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
_ENFORCER = None


def init(policy_file=None, rules=None, default_rule=None, use_conf=True):
    """Init an Enforcer class.

    :param policy_file: Custom policy file to use, if none is specified,
        `CONF.oslo_policy.policy_file` will be used.
    :param rules: Default dictionary / Rules to use. It will be
        considered just in the first instantiation.
    :param default_rule: Default rule to use, CONF.oslo_policy.default_rule
        will be used if none is specified.
    :param use_conf: Whether to load rules from config file.
    """

    global _ENFORCER

    if not _ENFORCER:
        _ENFORCER = policy.Enforcer(CONF,
                                    policy_file='policy.yaml',
                                    rules=rules,
                                    default_rule=default_rule,
                                    use_conf=use_conf)
        register_rules(_ENFORCER)


def enforce(action):

    init()

    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            context = args[1].context
            credentials = context.to_policy_values()
            exc = errors.PolicyNotAuthorized

            try:
                _ENFORCER.enforce(action, {}, context.to_dict(), do_raise=True,
                                  exc=exc, action=action)
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
