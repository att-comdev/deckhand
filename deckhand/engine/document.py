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

import six


class Document(object):
    """Object wrapper for documents."""

    def __init__(self, data):
        """Constructor for ``Document``.

        :param data: Dictionary of all document data (includes metadata, data,
            schema, etc.).
        """
        self._inner = data

    @property
    def all_data(self):
        return self._inner

    def set_data(self, value, key=None):
        if not key:
            self._inner = value
        else:
            self._inner[key] = value[key]

    def is_abstract(self):
        try:
            abstract = self._inner['metadata']['layeringDefinition']['abstract']
            return six.text_type(abstract) == 'True'
        except KeyError:
            return False

    def get_name(self):
        return self._inner['metadata']['name']

    def get_layer(self):
        return self._inner['metadata']['layeringDefinition']['layer'].lower()

    def get_parent_selector(self):
        """Return the `parentSelector` for the document.

        The topmost document defined by the `layerOrder` in the LayeringPolicy
        does not have a `parentSelector` as it has no parent.

        :returns: `parentSelcetor` for the document if present, else None.
        """
        try:
            return self._inner['metadata']['layeringDefinition'][
                'parentSelector']
        except KeyError:
            return None

    def get_labels(self):
        return self._inner['metadata']['labels']

    def get_actions(self):
        try:
            return self._inner['metadata']['layeringDefinition']['actions']
        except KeyError:
            return []

    def get_children(self, nested=False):
        if not nested:
            return self._inner.get('children', [])
        else:
            return self._get_nested_children(self, [])

    def _get_nested_children(self, doc, nested_children):
        for child in doc.get('children', []):
            nested_children.append(child)
            if 'children' in child._inner:
                self._get_nested_children(child, nested_children)
        return nested_children

    def get(self, k, default):
        return self.__getitem__(k, default=default)

    def __getitem__(self, k, default=None):
        return self._inner.get(k, default)

    def __delitem__(self, k):
        if self.__contains__(k):
            del self._inner[k]

    def __contains__(self, k):
        return self.get(k, default=None) is not None

    def __missing__(self, k):
        return not self.__contains__(k)

    def __repr__(self):
        return repr(self._inner)
