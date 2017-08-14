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
import inspect
import string

import falcon


def to_camel_case(s):
    return (s[0].lower() + string.capwords(s, sep='_').replace('_', '')[1:]
            if s else s)


class ViewBuilder(object):
    """Model API responses as dictionaries."""

    _collection_name = None

    def _gen_url(self, revision):
        # TODO(fmontei): Use a config-based url for the base url below.
        base_url = 'https://deckhand/api/v1.0/%s/%s'
        return base_url % (self._collection_name, revision.get('id'))


def enforce_content_types(valid_content_types):
    """Decorator handling content type enforcement on behalf of REST verbs."""

    if not isinstance(valid_content_types, list):
        valid_content_types = [valid_content_types]

    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, req, *func_args, **func_kwargs):
            content_type = (req.content_type.split(';', 1)[0].strip()
                            if req.content_type else '')

            if not content_type:
                raise falcon.HTTPMissingHeader('Content-Type')
            elif content_type not in valid_content_types:
                message = (
                    "Unexpected content type: {type}. Expected content types "
                    "are: {expected}."
                ).format(
                    type=req.content_type.decode('utf-8'),
                    expected=valid_content_types
                )
                raise falcon.HTTPUnsupportedMediaType(description=message)

            return f(self, req, *func_args, **func_kwargs)

        return wrapper

    return decorator


def reroute(on):
    """Decorator for routing GET request to list or show implementation.

    Re-routes the request to the show or list implementation depending on
    whether the ``on`` condition is contained in the kwargs passed to the
    ``on_get`` handler.

    Requires that the class of the function to which the decorator is applied
    implement ``on_show`` and ``on_list``.

    :param: The condition on which to call ``on_show`` if it is present
        in the list of kwargs passed to ``on_get``. Else ``on_list`` is called.
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *func_args, **func_kwargs):

            required_helpers = ['on_show', 'on_list']
            for func in required_helpers:
                if (not hasattr(self.__class__, func)
                    or not inspect.ismethod(getattr(self.__class__, func))):
                    raise TypeError('The class of the function to which this '
                                    'decorator is applied must implement: %s.'
                                    % required_helpers)

            if on in func_kwargs:
                func = getattr(self, "on_show")
            else:
                func = getattr(self, "on_list")

            return func(*func_args, **func_kwargs)

        return wrapper

    return decorator
