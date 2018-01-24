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

from . import errors
from .document import CompleteDocument
import copy
import jsonpath_ng
import logging

__all__ = ['extract', 'inject']

LOG = logging.getLogger(__name__)


def extract(doc, path):
    p, path_errors = _p(path)
    if path_errors:
        return None, [
            errors.JSONPathExtractError(
                '%s: %s' % (doc.full_name, path), causes=path_errors)
        ]

    value, get_errors = _jp_get(doc, p)
    if not get_errors:
        return value, []
    else:
        return None, [
            errors.JSONPathExtractError(
                '%s: %s' % (doc.full_name, path), causes=get_errors)
        ]


def inject(doc, value, path, pattern=None):
    p, path_errors = _p(path)
    if path_errors:
        return None, [
            errors.JSONPathInjectError(
                '%s: %s (pattern=%s)' % (doc.full_name, path, pattern),
                causes=path_errors)
        ]

    if pattern is None:
        return _inject_into_path(doc, value, p)
    else:
        return _inject_into_pattern(doc, value, p, pattern)


def _jp_get(doc, p):
    matches = p.find(doc.data)
    if matches:
        return matches[0].value, []
    else:
        return None, [errors.JSONPathGetError('%s: %s' % (doc.full_name, p))]


def _inject_into_path(doc, value, p):
    inject_errors = []

    data_section = doc.data
    result_data = p.update(data_section, value)
    update_value, update_errors = _jp_get(doc, p)

    if (update_errors or update_value != value):
        inject_errors.extend(update_errors)
        result_data, vivify_errors = _jp_vivify(doc, value, p)
        inject_errors.extend(vivify_errors)

    doc_dict = doc.as_dict
    if result_data is not None:
        doc_dict['data'] = result_data

    result = CompleteDocument(doc_dict)
    if not inject_errors:
        return result, []
    else:
        return None, [errors.JSONPathInjectError(causes=inject_errors)]


def _inject_into_pattern(doc, data, p, pattern):
    return None, [errors.WIP('inject into pattern')]


def _jp_vivify(doc, value, p):
    # NOTE(mark-burnett): ideally we could walk the jsonpath AST and expand
    # this to support array vivification.  At that point, we should probably
    # try hard to upstream these improvements (there is already some
    # autovivification of array elements in jsonpath_ng now).
    path = str(p)
    data_section = copy.deepcopy(doc.data)
    d = data_section
    for part in path.split('.')[1:]:
        if part not in d:
            d[part] = {}
        d = d[part]

    # XXX WIP
    result_data = p.update(data_section, value)

    return None, [errors.WIP('vivify')]


def _p(raw_path):
    if raw_path == '.':
        path = '$'
    elif raw_path.startswith('.'):
        path = '$' + raw_path
    else:
        path = raw_path

    try:
        return jsonpath_ng.parse(path), []
    except Exception:
        return None, [errors.JSONPathParseError('%s' % raw_path)]
