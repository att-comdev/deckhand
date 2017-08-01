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

import collections
import copy

from deckhand.engine import document
from deckhand.engine import utils
from deckhand import errors


class DocumentLayering(object):
    """Class responsible for handling document layering.

    Layering is controlled in two places:

    1. The `LayeringPolicy` control document, which defines the valid layers
       and their order of precedence.
    2. In the `metadata.layeringDefinition` section of normal
       (`metadata.schema=metadata/Document/v1`) documents.

    .. note::

        Only documents with the same `schema` are allowed to be layered
        together into a fully rendered document.
    """

    SUPPORTED_METHODS = ('merge', 'replace', 'delete')
    LAYERING_POLICY_SCHEMA = 'deckhand/LayeringPolicy/v1'

    def __init__(self, documents):
        """Contructor for ``DocumentLayering``.

        :param documents: List of YAML documents represented as dictionaries.
        """
        self.documents = [document.Document(d) for d in documents]
        self._find_layering_policy()
        self.layered_docs = self._calc_document_children()

    def render(self):
        """Perform layering on the set of `documents`.

        Each concrete document will undergo layering according to the actions
        defined by its `layeringDefinition`.

        :returns: the list of rendered documents (does not include layering
            policy document).
        """
        # ``rendered_data_by_layer`` agglomerates the set of changes across all
        # actions across each layer for a specific document. Use copy
        # to prevent global data from being updated referentially.
        rendered_data_by_layer = {}

        # NOTE(fmontei): ``global_docs`` represents the topmost documents in
        # the system. It should probably be impossible for more than 1
        # top-level doc to exist, but handle multiple for now.
        global_docs = [doc for doc in self.layered_docs
                       if doc.get_layer() == self.layer_order[0]]

        for doc in global_docs:
            layer_idx = self.layer_order.index(doc.get_layer())
            rendered_data_by_layer[layer_idx] = copy.deepcopy(doc.all_data)

            # Keep iterating as long as a child exists.
            for child in doc.get_children(nested=True):
                # Retrieve the most up-to-date rendered_data (by
                # referencing the child's parent's data).
                child_layer_idx = self.layer_order.index(child.get_layer())
                rendered_data = rendered_data_by_layer[child_layer_idx - 1]

                # Apply each action to the current document.
                actions = child.get_actions()
                for action in actions:
                    self._apply_action(action, child.all_data, rendered_data)

                # Update the actual document data in the outer for loop.
                if not child.is_abstract():
                    child.set_data(copy.deepcopy(rendered_data), key='data')

                # Update ``rendered_data_by_layer`` for this layer so that
                # children in deeper layers can reference the most up-to-date
                # changes.
                rendered_data_by_layer[child_layer_idx] = copy.deepcopy(
                    rendered_data)
                
            if 'children' in doc:
                del doc['children']

        return [d.all_data for d in self.layered_docs]

    def _apply_action(self, action, child_data, overall_data):
        """Apply actions to each layer that is rendered.

        Supported actions are:

            * `merge` - a "deep" merge that layers new and modified data onto
              existing data
            * `replace` - overwrite data at the specified path and replace it
              with the data given in this document
            * `delete` - remove the data at the specified path

        Requirements:

            * The path must be present in both ``child_data`` and
              ``overall_data`` (in both the parent and child documents).
        """
        # NOTE: In order to use references to update nested entries inside the
        # ``overall_data`` dict, mutable data must be manipulated. That is,
        # only references to dictionaries and lists and other mutable data
        # types are allowed. In the event that the path is ".", the entire
        # document is passed so that doc["data"] can be manipulated via
        # references.

        method = action['method']
        if method not in self.SUPPORTED_METHODS:
            raise errors.UnsupportedActionMethod(
                action=action, document=child_data)

        # Remove empty string paths and ensure that "data" is always present.
        path = action['path'].split('.')
        path = [p for p in path if p != '']
        path.insert(0, 'data')
        last_key = 'data' if not path[-1] else path[-1]

        for attr in path:
            if attr == path[-1]:
                break
            overall_data = overall_data.get(attr)
            child_data = child_data.get(attr)

        if method == 'delete':
            # If the entire document is passed (i.e. the dict including
            # metadata, data, schema, etc.) then reset data to an empty dict.
            if last_key == 'data':
                overall_data['data'] = {}
            elif last_key in overall_data:
                del overall_data[last_key]
            else:
                # If the key does not exist in `overall_data`, this is a
                # validation error.
                raise errors.MissingDocumentKey(
                    child=child_data, parent=overall_data, key=last_key)
        elif method == 'merge':
            if last_key in overall_data and last_key in child_data:
                # If both entries are dictionaries, do a deep merge. Otherwise
                # do a simple merge.
                if (isinstance(overall_data[last_key], dict)
                    and isinstance(child_data[last_key], dict)):
                    utils.deep_merge(
                        overall_data[last_key], child_data[last_key])
                else:
                    overall_data.setdefault(last_key, child_data[last_key])
            elif last_key in child_data:
                overall_data.setdefault(last_key, child_data[last_key])
            else:
                # If the key does not exist in the child document, this is a
                # validation error.
                raise errors.MissingDocumentKey(
                    child=child_data, parent=overall_data, key=last_key)
        elif method == 'replace':
            if last_key in overall_data and last_key in child_data:
                overall_data[last_key] = child_data[last_key]
            elif last_key in child_data:
                overall_data.setdefault(last_key, child_data[last_key])
            else:
                # If the key does not exist in the child document, this is a
                # validation error.
                raise errors.MissingDocumentKey(
                    child=child_data, parent=overall_data, key=last_key)

    def _find_layering_policy(self):
        """Retrieve the current layering policy.

        :raises LayeringPolicyMalformed: If the `layerOrder` could not be
            found in the LayeringPolicy or if it is not a list.
        :raises LayeringPolicyNotFound: If system has no layering policy.
        """
        # TODO(fmontei): There should be a DB call here to fetch the layering
        # policy from the DB.
        for doc in self.documents:
            if doc.all_data['schema'] == self.LAYERING_POLICY_SCHEMA:
                self.layering_policy = doc
                break

        if not hasattr(self, 'layering_policy'):
            raise errors.LayeringPolicyNotFound(
                schema=self.LAYERING_POLICY_SCHEMA)

        # TODO(fmontei): Rely on schema validation or some such for this.
        try:
            self.layer_order = list(self.layering_policy['data']['layerOrder'])
        except KeyError:
            raise errors.LayeringPolicyMalformed(
                schema=self.LAYERING_POLICY_SCHEMA,
                document=self.layering_policy)

        if not isinstance(self.layer_order, list):
            raise errors.LayeringPolicyMalformed(
                schema=self.LAYERING_POLICY_SCHEMA,
                document=self.layering_policy)

    def _calc_document_children(self):
        """Determine each document's children.

        For each document, attempts to find the document's children. Adds a new
        key called "children" to the document's dictionary.

        .. note::

            A document should only have exactly one parent.

            If a document does not have a parent, then its layer must be
            the topmost layer defined by the `layerOrder`.

        :returns: Ordered list of documents that need to be layered. Each
            document contains a "parent" in addition to original data. The
            order highest to lowest layer in `layerOrder`.
        :raises IndeterminateDocumentParent: If more than one parent document
            was found for a document.
        :raises MissingDocumentParent: If the parent document could not be
            found. Only applies documents with `layeringDefinition` property.
        """
        layered_docs = list(
            filter(lambda x: 'layeringDefinition' in x['metadata'],
                self.documents))

        all_children = collections.Counter()
        def _get_children(doc):
            children = []
            doc_layer = doc.get_layer()
            try:
                next_layer_idx = self.layer_order.index(doc_layer) + 1
                children_doc_layer = self.layer_order[next_layer_idx]
            except IndexError:
                # The lowest layer has been reached, so no children. Return
                # empty list.
                return children

            for other_doc in layered_docs:
                other_doc_layer = other_doc.get_layer()
                if other_doc_layer == children_doc_layer:
                    # A document can have many labels but should only have one
                    # explicit label for the parentSelector.
                    parent_sel = other_doc.get_parent_selector()
                    parent_sel_key = list(parent_sel.keys())[0]
                    parent_sel_val = list(parent_sel.values())[0]
                    doc_labels = doc.get_labels()

                    if (parent_sel_key in doc_labels and
                        parent_sel_val == doc_labels[parent_sel_key]):
                        children.append(other_doc)

            return children

        for layer in self.layer_order:
            docs_by_layer = list(filter(
                (lambda x: x.get_layer() == layer), layered_docs))

            for doc in docs_by_layer:
                children = _get_children(doc)

                if children:
                    all_children.update(children)
                    doc.all_data.setdefault('children', children)

        all_children_elements = list(all_children.elements())
        secondary_docs = list(
            filter(lambda d: d.get_layer() != self.layer_order[0], layered_docs))
        for doc in secondary_docs:
            # Unless the document is the topmost document in the
            # `layerOrder` of the LayeringPolicy, it should be a child document
            # of another document.
            if doc not in all_children_elements:
                raise errors.MissingDocumentParent(document=doc)
            # If the document is a child document of more than 1 parent, then
            # the document has too many parents, which is a validation error.
            elif all_children[doc] != 1:
                raise errors.IndeterminateDocumentParent(document=doc)

        return layered_docs
