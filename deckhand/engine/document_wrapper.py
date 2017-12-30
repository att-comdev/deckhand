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

from oslo_serialization import jsonutils as json

from deckhand import utils


class DocumentWrapper(dict):
    """Wrapper for a document.

    Useful for accessing nested dictionary keys without having to worry about
    exceptions getting thrown.
    """

    @property
    def is_abstract(self):
        return utils.jsonpath_parse(
            self, 'metadata.layeringDefinition.abstract') is True

    @property
    def schema(self):
        return self.get('schema', '')

    @property
    def metadata(self):
        return self.get('metadata', {})

    @property
    def name(self):
        return utils.jsonpath_parse(self, 'metadata.name')

    @property
    def layer(self):
        return utils.jsonpath_parse(
            self, 'metadata.layeringDefinition.layer')

    @property
    def parent_selector(self):
        return utils.jsonpath_parse(
            self, 'metadata.layeringDefinition.parentSelector') or {}

    @property
    def labels(self):
        return utils.jsonpath_parse(self, 'metadata.labels') or {}

    @property
    def substitutions(self):
        return utils.jsonpath_parse(self, 'metadata.substitutions') or []

    @property
    def actions(self):
        return utils.jsonpath_parse(
            self, 'metadata.layeringDefinition.actions') or []

    @property
    def children(self):
        """Recursively retrieve all children.

        Used in the layering module when calculating children for each
        document.

        :returns: List of nested children.
        :rtype: Generator[:class:`DocumentWrapper`]
        """
        return self._get_children(self)

    def _get_children(self, document):
        for child in document.get('children', []):
            yield child
            grandchildren = self._get_children(child)
            for grandchild in grandchildren:
                yield grandchild

    def __hash__(self):
        return hash(json.dumps(self, sort_keys=True))
