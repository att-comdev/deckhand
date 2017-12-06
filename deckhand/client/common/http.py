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

import copy
import logging
import socket

from keystoneauth1 import adapter
from keystoneauth1 import exceptions as ksa_exc
import OpenSSL
from oslo_utils import importutils
from oslo_utils import netutils
import requests
import six

try:
    import json
except ImportError:
    import simplejson as json

from oslo_utils import encodeutils

from glanceclient.common import utils
from glanceclient import exc

LOG = logging.getLogger(__name__)
USER_AGENT = 'python-deckhandclient'
CHUNKSIZE = 1024 * 64  # 64kB


def encode_headers(headers):
    """Encodes headers.

    Note: This should be used right before
    sending anything out.

    :param headers: Headers to encode
    :returns: Dictionary with encoded headers'
              names and values
    """
    return dict((encodeutils.safe_encode(h), encodeutils.safe_encode(v))
                for h, v in headers.items() if v is not None)


class _BaseHTTPClient(object):

    @staticmethod
    def _chunk_body(body):
        chunk = body
        while chunk:
            chunk = body.read(CHUNKSIZE)
            if not chunk:
                break
            yield chunk

    def _set_common_request_kwargs(self, headers, kwargs):
        """Handle the common parameters used to send the request."""

        # Default Content-Type is octet-stream
        content_type = headers.get('Content-Type', 'application/octet-stream')

        # NOTE(jamielennox): remove this later. Managers should pass json= if
        # they want to send json data.
        data = kwargs.pop("data", None)
        if data is not None and not isinstance(data, six.string_types):
            try:
                data = json.dumps(data)
                content_type = 'application/json'
            except TypeError:
                # Here we assume it's a file-like object and we'll chunk it
                data = self._chunk_body(data)

        headers['Content-Type'] = content_type
        kwargs['stream'] = content_type == 'application/octet-stream'

        return data

    def _handle_response(self, resp):
        if not resp.ok:
            LOG.debug("Request returned failure status %s.", resp.status_code)
            raise exc.from_response(resp, resp.content)
        elif (resp.status_code == requests.codes.MULTIPLE_CHOICES and
              resp.request.path_url != '/versions'):
            # NOTE(flaper87): Eventually, we'll remove the check on `versions`
            # which is a bug (1491350) on the server.
            raise exc.from_response(resp)

        content_type = resp.headers.get('Content-Type')

        # Read body into string if it isn't obviously image data
        if content_type == 'application/octet-stream':
            # Do not read all response in memory when downloading an image.
            body_iter = _close_after_stream(resp, CHUNKSIZE)
        else:
            content = resp.text
            if content_type and content_type.startswith('application/json'):
                # Let's use requests json method, it should take care of
                # response encoding
                body_iter = resp.json()
            else:
                body_iter = six.StringIO(content)
                try:
                    body_iter = json.loads(''.join([c for c in body_iter]))
                except ValueError:
                    body_iter = None

        return resp, body_iter


class HTTPClient(_BaseHTTPClient):

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.identity_headers = kwargs.get('identity_headers')
        self.auth_token = kwargs.get('token')
        if self.identity_headers:
            self.auth_token = self.identity_headers.pop('X-Auth-Token',
                                                        self.auth_token)

        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

        self.timeout = float(kwargs.get('timeout', 600))

        if self.endpoint.startswith("https"):

            if kwargs.get('insecure', False) is True:
                self.session.verify = False
            else:
                if kwargs.get('cacert', None) is not '':
                    self.session.verify = kwargs.get('cacert', True)

            self.session.cert = (kwargs.get('cert_file'),
                                 kwargs.get('key_file'))

    @staticmethod
    def parse_endpoint(endpoint):
        return netutils.urlsplit(endpoint)

    def log_curl_request(self, method, url, headers, data, kwargs):
        curl = ['curl -g -i -X %s' % method]

        headers = copy.deepcopy(headers)
        headers.update(self.session.headers)

        for (key, value) in headers.items():
            header = '-H \'%s: %s\'' % utils.safe_header(key, value)
            curl.append(header)

        if not self.session.verify:
            curl.append('-k')
        else:
            if isinstance(self.session.verify, six.string_types):
                curl.append(' --cacert %s' % self.session.verify)

        if self.session.cert:
            curl.append(' --cert %s --key %s' % self.session.cert)

        if data and isinstance(data, six.string_types):
            curl.append('-d \'%s\'' % data)

        curl.append(url)

        msg = ' '.join([encodeutils.safe_decode(item, errors='ignore')
                        for item in curl])
        LOG.debug(msg)

    @staticmethod
    def log_http_response(resp):
        status = (resp.raw.version / 10.0, resp.status_code, resp.reason)
        dump = ['\nHTTP/%.1f %s %s' % status]
        headers = resp.headers.items()
        dump.extend(['%s: %s' % utils.safe_header(k, v) for k, v in headers])
        dump.append('')
        content_type = resp.headers.get('Content-Type')

        if content_type != 'application/octet-stream':
            dump.extend([resp.text, ''])
        LOG.debug('\n'.join([encodeutils.safe_decode(x, errors='ignore')
                             for x in dump]))

    def _request(self, method, url, **kwargs):
        """Send an http request with the specified characteristics.

        Wrapper around httplib.HTTP(S)Connection.request to handle tasks such
        as setting headers and error handling.
        """
        # Copy the kwargs so we can reuse the original in case of redirects
        headers = copy.deepcopy(kwargs.pop('headers', {}))

        if self.identity_headers:
            for k, v in self.identity_headers.items():
                headers.setdefault(k, v)

        data = self._set_common_request_kwargs(headers, kwargs)

        # add identity header to the request
        if not headers.get('X-Auth-Token'):
            headers['X-Auth-Token'] = self.auth_token

        # Note(flaper87): Before letting headers / url fly,
        # they should be encoded otherwise httplib will
        # complain.
        headers = encode_headers(headers)

        if self.endpoint.endswith("/") or url.startswith("/"):
            conn_url = "%s%s" % (self.endpoint, url)
        else:
            conn_url = "%s/%s" % (self.endpoint, url)
        self.log_curl_request(method, conn_url, headers, data, kwargs)

        try:
            resp = self.session.request(method,
                                        conn_url,
                                        data=data,
                                        headers=headers,
                                        **kwargs)
        except requests.exceptions.Timeout as e:
            message = ("Error communicating with %(url)s: %(e)s" %
                       dict(url=conn_url, e=e))
            raise exc.InvalidEndpoint(message=message)
        except requests.exceptions.ConnectionError as e:
            message = ("Error finding address for %(url)s: %(e)s" %
                       dict(url=conn_url, e=e))
            raise exc.CommunicationError(message=message)
        except socket.gaierror as e:
            message = "Error finding address for %s: %s" % (
                self.endpoint_hostname, e)
            raise exc.InvalidEndpoint(message=message)
        except (socket.error, socket.timeout, IOError) as e:
            endpoint = self.endpoint
            message = ("Error communicating with %(endpoint)s %(e)s" %
                       {'endpoint': endpoint, 'e': e})
            raise exc.CommunicationError(message=message)
        except OpenSSL.SSL.Error as e:
            message = ("SSL Error communicating with %(url)s: %(e)s" %
                       {'url': conn_url, 'e': e})
            raise exc.CommunicationError(message=message)

        resp, body_iter = self._handle_response(resp)
        self.log_http_response(resp)
        return resp, body_iter

    def head(self, url, **kwargs):
        return self._request('HEAD', url, **kwargs)

    def get(self, url, **kwargs):
        return self._request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self._request('POST', url, **kwargs)

    def put(self, url, **kwargs):
        return self._request('PUT', url, **kwargs)

    def patch(self, url, **kwargs):
        return self._request('PATCH', url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request('DELETE', url, **kwargs)


def _close_after_stream(response, chunk_size):
    """Iterate over the content and ensure the response is closed after."""
    # Yield each chunk in the response body
    for chunk in response.iter_content(chunk_size=chunk_size):
        yield chunk
    # Once we're done streaming the body, ensure everything is closed.
    # This will return the connection to the HTTPConnectionPool in urllib3
    # and ideally reduce the number of HTTPConnectionPool full warnings.
    response.close()


class SessionClient(adapter.Adapter, _BaseHTTPClient):

    def __init__(self, session, **kwargs):
        kwargs.setdefault('user_agent', USER_AGENT)
        super(SessionClient, self).__init__(session, **kwargs)

    def request(self, url, method, **kwargs):
        headers = kwargs.pop('headers', {})

        kwargs['raise_exc'] = False
        data = self._set_common_request_kwargs(headers, kwargs)
        try:
            # NOTE(pumaranikar): To avoid bug #1641239, no modification of
            # headers should be allowed after encode_headers() is called.
            resp = super(SessionClient,
                         self).request(url,
                                       method,
                                       headers=encode_headers(headers),
                                       data=data,
                                       **kwargs)
        except ksa_exc.ConnectTimeout as e:
            conn_url = self.get_endpoint(auth=kwargs.get('auth'))
            conn_url = "%s/%s" % (conn_url.rstrip('/'), url.lstrip('/'))
            message = ("Error communicating with %(url)s %(e)s" %
                       dict(url=conn_url, e=e))
            raise exc.InvalidEndpoint(message=message)
        except ksa_exc.ConnectFailure as e:
            conn_url = self.get_endpoint(auth=kwargs.get('auth'))
            conn_url = "%s/%s" % (conn_url.rstrip('/'), url.lstrip('/'))
            message = ("Error finding address for %(url)s: %(e)s" %
                       dict(url=conn_url, e=e))
            raise exc.CommunicationError(message=message)

        return self._handle_response(resp)


def get_http_client(endpoint=None, session=None, **kwargs):
    if session:
        return SessionClient(session, **kwargs)
    elif endpoint:
        return HTTPClient(endpoint, **kwargs)
    else:
        raise AttributeError('Constructing a client must contain either an '
                             'endpoint or a session')
