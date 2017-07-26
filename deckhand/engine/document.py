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

        :param data: Dictionary of all document data.
        """
        self.data = data

    def set_data(self, data, key=None):
        if not key:
            self.data = data
        else:
            self.data[key] = data[key]

    def is_abstract(self):
        try:
            abstract = self.data['metadata']['layeringDefinition']['abstract']
            return six.text_type(abstract) == 'True'
        except KeyError:
            return False

    def get_layer(self):
        return self.data['metadata']['layeringDefinition']['layer'].lower()

    def get_parent_selector(self):
        """Return the `parentSelector` for the document.

        The topmost document defined by the `layerOrder` in the LayeringPolicy
        does not have a `parentSelector` as it has no parent.

        :returns: `parentSelcetor` for the document if present, else None.
        """
        try:
            return self.data['metadata']['layeringDefinition'][
                'parentSelector']
        except KeyError:
            return None

    def get_labels(self):
        return self.data['metadata']['labels']

    def get_actions(self):
        try:
            return self.data['metadata']['layeringDefinition']['actions']
        except KeyError:
            return []

    def __getitem__(self, k):
        return self.data[k]

    def __repr__(self):
        return repr(self.data)
