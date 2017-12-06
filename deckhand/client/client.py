# Copyright 2017 AT&T Intellectual Property.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from deckhand.client.common import http
from deckhand.client.common import utils
from deckhand.client import buckets


class Client(object):
    """Client for the Deckhand v1.0 API.

    :param string endpoint: A user-supplied endpoint URL for the Deckhand
                            service.
    :param string token: Token for authentication.

    """

    def __init__(self, endpoint=None, token=None, **kwargs):
        endpoint, self.version = utils.endpoint_version_from_url(endpoint, 1.0)
        self.http_client = http.get_http_client(endpoint=endpoint, **kwargs)
        self.buckets = buckets.Controller(self.http_client)
