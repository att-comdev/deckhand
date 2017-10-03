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

import re
import string

import jsonpath_ng

from deckhand import errors


def to_camel_case(s):
    """Convert string to camel case."""
    return (s[0].lower() + string.capwords(s, sep='_')
            .replace('_', '')[1:] if s else s)


def to_snake_case(name):
    """Convert string to snake case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def jsonpath_parse(document, jsonpath):
    """Parse value given JSON path in the document.

    Check for nested attributes included in "dest" attributes in the data
    section of the YAML file. For example, a "dest" attribute of
    ".foo.bar.baz" should mean that the YAML data adheres to:

    .. code-block:: yaml

       ---
       foo:
           bar:
               baz: <data_to_be_substituted_here>

    :param document: The section of data in the YAML document that
        is intended to be substituted with secrets.
    :param jsonpath: A multi-part key that references nested data in the
        substitutable part of the YAML data, e.g. ".foo.bar.baz".
    :returns: nested entry in ``dict_data`` if present; else None.
    """
    if jsonpath.startswith('.'):
        jsonpath = '$' + jsonpath

    p = jsonpath_ng.parse(jsonpath)
    matches = p.find(document)
    if matches:
        return matches[0].value


def jsonpath_replace(document, value, jsonpath, pattern=None):
    """Update value in document at the path specified by ``jsonpath``.

    If the nested path corresponding to ``jsonpath`` isn't found in the
    document, the path is created as an empty ``{}`` for each iteration.

    :param document: The section of data in the YAML document that
        is intended to be substituted with secrets.
    :param value: The new value for document[jsonpath].
    :param jsonpath: A multi-part key that references nested data in the
        substitutable part of the YAML data, e.g. ".foo.bar.baz".
    :returns: nested entry in ``dict_data`` if present; else None.
    """
    document = document.copy()
    if jsonpath.startswith('.'):
        jsonpath = '$' + jsonpath

    def _do_replace():
        p = jsonpath_ng.parse(jsonpath)
        p_to_change = p.find(document)

        if p_to_change:
            _value = value
            if pattern:
                to_replace = p_to_change[0].value
                _value = to_replace.replace(pattern, value)
            return p.update(document, _value)

    result = _do_replace()
    if result:
        return result

    # A pattern requires us to look up the data located at document[jsonpath]
    # and then figure out what re.match(document[jsonpath], pattern) is (in
    # pseudocode). But raise an exception in case the path isn't present in the
    # document and a pattern has been provided since it is impossible to do the
    # look up.
    if pattern:
        raise errors.MissingDocumentPattern(data=document)

    # However, Deckhand should be smart enough to create the nested keys in the
    # document if they don't exist and a pattern isn't required.
    doc = document
    for path in jsonpath.split('.')[1:]:
        if path not in doc:
            doc.setdefault(path, {})
        doc = doc.get(path)

    return _do_replace()
