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

import falcon
from oslo_log import log as logging

from deckhand import errors as deckhand_errors

LOG = logging.getLogger(__name__)


class ViewBuilder(object):
    """Model API responses as dictionaries."""

    _collection_name = None

    def _gen_url(self, revision):
        # TODO(fmontei): Use a config-based url for the base url below.
        base_url = 'https://deckhand/api/v1.0/%s/%s'
        return base_url % (self._collection_name, revision.get('id'))


def sanitize_params(allowed_params):
    """Sanitize query string parameters passed to an HTTP request.

    Overrides the ``params`` attribute in the ``req`` object with the sanitized
    params. Invalid parameters are ignored.

    :param allowed_params: The request's query string parameters.
    """
    # A mapping between the filter keys users provide and the actual DB
    # representation of the filter.
    _mapping = {
        # Mappings for revision documents.
        'status.bucket': 'bucket_name',
        'metadata.label': 'metadata.labels',
        # Mappings for revisions.
        'tag': 'tags.[*].tag'
    }

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, req, *func_args, **func_kwargs):
            req_params = req.params or {}
            sanitized_params = {}

            def _convert_to_dict(sanitized_params, filter_key, filter_val):
                # Key-value pairs like metadata.label=foo=bar need to be
                # converted to {'metadata.label': {'foo': 'bar'}} because
                # 'metadata.labels' in a document is a dictionary. Later,
                # we can check whether the filter dict is a subset of the
                # actual dict for metadata labels.
                for val in list(filter_val):
                    if '=' in val:
                        sanitized_params.setdefault(filter_key, {})
                        pair = val.split('=')
                        try:
                            sanitized_params[filter_key][pair[0]] = pair[1]
                        except IndexError:
                            pass

            for key, val in req_params.items():
                if not isinstance(val, list):
                    val = [val]
                is_key_val_pair = '=' in val[0]
                if key in allowed_params:
                    if key in _mapping:
                        if is_key_val_pair:
                            _convert_to_dict(
                                sanitized_params, _mapping[key], val)
                        else:
                            sanitized_params[_mapping[key]] = req_params[key]
                    else:
                        if is_key_val_pair:
                            _convert_to_dict(sanitized_params, key, val)
                        else:
                            sanitized_params[key] = req_params[key]

            func_args = func_args + (sanitized_params,)
            return func(self, req, *func_args, **func_kwargs)

        return wrapper

    return decorator


def expected_errors(errors):
    """Decorator for raising expected exceptions as ``falcon``-based errors.
    Unexpected exceptions are raised as ``falcon.HTTPInternalServerError``.

    Deckhand only raises 400, 403, 404 and 409 exceptions from controllers, so
    these are the only conversions that need to be handled.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as exc:
                if isinstance(exc, deckhand_errors.DeckhandException):
                    if isinstance(errors, int):
                        t_errors = (errors,)
                    else:
                        t_errors = errors
                    if exc.code in t_errors:
                        falcon_exc = _get_falcon_error_from_code(exc.code)
                        raise falcon_exc(description=exc.format_message())
                elif isinstance(exc, falcon.HTTPError):
                    raise

                LOG.exception("Unexpected exception in API method")
                msg = 'Unexpected API Error. %s' % type(exc)
                raise falcon.HTTPInternalServerError(description=msg)

        return wrapped

    return decorator


def _get_falcon_error_from_code(code):
    if code == 400:
        return falcon.HTTPBadRequest
    elif code == 403:
        return falcon.HTTPForbidden
    elif code == 404:
        return falcon.HTTPNotFound
    elif code == 409:
        return falcon.HTTPConflict
    else:
        return falcon.HTTPInternalServerError
