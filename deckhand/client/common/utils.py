# Copyright 2012 OpenStack Foundation
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

import hashlib
import re

import six
import six.moves.urllib.parse as urlparse


SENSITIVE_HEADERS = ('X-Auth-Token', )


def safe_header(name, value):
    if value is not None and name in SENSITIVE_HEADERS:
        h = hashlib.sha1(value)
        d = h.hexdigest()
        return name, "{SHA1}%s" % d
    else:
        return name, value


def endpoint_version_from_url(endpoint, default_version=None):
    if endpoint:
        endpoint, version = strip_version(endpoint)
        return endpoint, version or default_version
    else:
        return None, default_version


def strip_version(endpoint):
    """Strip version from the last component of endpoint if present."""
    # NOTE(flaper87): This shouldn't be necessary if
    # we make endpoint the first argument. However, we
    # can't do that just yet because we need to keep
    # backwards compatibility.
    if not isinstance(endpoint, six.string_types):
        raise ValueError("Expected endpoint")

    version = None
    # Get rid of trailing '/' if present
    endpoint = endpoint.rstrip('/')
    url_parts = urlparse.urlparse(endpoint)
    (scheme, netloc, path, __, __, __) = url_parts
    path = path.lstrip('/')
    # regex to match 'v1' or 'v2.0' etc
    if re.match('v\d+\.?\d*', path):
        version = float(path.lstrip('v'))
        endpoint = scheme + '://' + netloc
    return endpoint, version
