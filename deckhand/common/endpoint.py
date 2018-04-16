# Copyright 2018 AT&T Intellectual Property.  All other rights reserved.
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

from keystoneauth1.exceptions.catalog import EndpointNotFound
from keystoneauth1 import loading
from keystoneauth1 import session

from deckhand.common import cache
from deckhand.conf import config
from deckhand import errors

CONF = config.CONF

MEMOIZE = cache.get_memoization_decorator(group='endpoint_cache')


@MEMOIZE
def get_own_endpoint():
    try:
        auth = loading.load_auth_from_conf_options(CONF, 'keystone_authtoken')
        sess = session.Session(auth=auth)
        endpoint = sess.get_endpoint(service_type='deckhand',
                                     interface='internal')
        return endpoint
    except EndpointNotFound:
        raise errors.DeckhandException(
            'Could not resolve own endpoint via Keystone endpoint lookup.')
