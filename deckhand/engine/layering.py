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
        self.layering_policy = self._find_layering_policy()
        self.layered_docs = self._calc_document_parents()

    def render(self):
        """Perform layering on the set of `documents`.

        Each concrete document will undergo layering according to the actions
        defined by its `layeringDefinition`.

        :returns: the list of rendered documents (does not include layering
            policy document).
        """
        # NOTE: In case performance becomes an issue, it is probably possible
        # to increase the performance of the layering process by changing
        # the logic below to do a top-bottom approach versus a bottom-up
        # approach. The bottom-up approach is slower because "intermediate"
        # layers need to be visited multiple times because lower layers depend
        # on higher layers, so higher layers can only be updated after lower
        # layers. The top-bottom approach should be faster because dependency
        # concerns won't come into play. The upper and lower layers can be
        # updated immediately, such that each document is visited only once.
        for doc in self.layered_docs:
            # ``rendered_data`` agglomerates the set of changes across all
            # actions across all layers for a specific document.
            rendered_data = doc.data

            # ``curr_data`` is a pointer to the current document that iterates
            # up the layers by following each document's parent until the
            # uppermost document layer-wise is reached.
            curr_data = doc
            # Keep iterating as long as a parent exists.
            while curr_data.get_parent_selector():
                # Perform all initializations with ``curr_data`` here so
                # if we continue below everything is ready for the next
                # iteration.
                actions = curr_data.get_actions()
                parent = curr_data['parent']
                if parent is None:
                    break
                curr_data = parent

                # Do not bother performing any actions if the document is
                # abstract since that is a waste of time.
                if doc.is_abstract():
                    continue

                # Apply each action to the current document.
                for action in actions:
                    self._apply_action(action, parent.data, rendered_data)

                # Update the actual document data in the outer for loop.
                doc.set_data(rendered_data, key='data')
                
        return [d.data for d in self.layered_docs]

    def _apply_action(self, action, parent_data, overall_data):
        """Apply actions to each layer that is rendered.

        Supported actions are:

            * `merge` - a "deep" merge that layers new and modified data onto
              existing data
            * `replace` - overwrite data at the specified path and replace it
              with the data given in this document
            * `delete` - remove the data at the specified path

        Requirements:

            * The path must be present in both ``parent_data`` and
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
                action=action, document=parent_data)

        # Remove empty string paths and ensure that "data" is always present.
        path = action['path'].split('.')
        path = [p for p in path if p != '']
        path.insert(0, 'data')
        last_key = 'data' if not path[-1] else path[-1]

        for attr in path:
            if attr == path[-1]:
                break
            overall_data = overall_data.get(attr)
            parent_data = parent_data.get(attr)

        if method == 'delete':
            # If the entire document is passed (i.e. the dict including
            # metadata, data, schema, etc.) then reset data to an empty dict.
            if last_key == 'data':
                overall_data['data'] = {}
            else:
                del overall_data[last_key]
        elif method == 'merge':
            if last_key in overall_data and last_key in parent_data:
                utils.deep_merge(overall_data[last_key], parent_data[last_key])
            # If the data does not exist in the source document, copy from
            # parent document.
            elif last_key in parent_data:
                overall_data.setdefault(last_key, parent_data[last_key])
        elif method == 'replace':
            if last_key in overall_data and last_key in parent_data:
                overall_data[last_key] = parent_data[last_key]
            # If the data does not exist in the source document, copy from
            # parent document.
            elif last_key in parent_data:
                overall_data.setdefault(last_key, parent_data[last_key])

    def _find_layering_policy(self):
        # FIXME(fmontei): There should be a DB call here to fetch the layering
        # policy from the DB.
        for doc in self.documents:
            if doc.data['schema'] == self.LAYERING_POLICY_SCHEMA:
                return doc
        raise errors.LayeringPolicyNotFound(schema=self.LAYERING_POLICY_SCHEMA)

    def _calc_document_parents(self):
        """Determine each document's parent.

        For each document, attempts to find the document's parent. Adds a new
        key called "parent" to the document's dictionary.

        .. note::

            A document should only have exactly one parent.

            If a document does not have a parent, then its layer must be
            the topmost layer defined by the `layerOrder`.

        :returns: Ordered list of documents that need to be layered. Each
            document contains a "parent" in addition to original data. The
            order highest to lowest layer in `layerOrder`.
        :raises LayeringPolicyMalformed: If the `layerOrder` could not be
            found in the LayeringPolicy or if it is not a list.
        :raises IndeterminateDocumentParent: If more than one parent document
            was found for a document.
        :raises MissingDocumentParent: If the parent document could not be
            found. Only applies documents with `layeringDefinition` property.
        """
        try:
            layer_order = list(
                reversed(self.layering_policy['data']['layerOrder']))
        except KeyError:
            raise errors.LayeringPolicyMalformed(
                schema=self.LAYERING_POLICY_SCHEMA,
                document=self.layering_policy)

        if not isinstance(layer_order, list):
            raise errors.LayeringPolicyMalformed(
                schema=self.LAYERING_POLICY_SCHEMA,
                document=self.layering_policy)

        layered_docs = list(
            filter(lambda x: 'layeringDefinition' in x['metadata'],
                self.documents))

        def _get_parents(doc):
            parents = []

            doc_layer = doc.get_layer()
            try:
                next_layer_idx = layer_order.index(doc_layer) + 1
                parent_doc_layer = layer_order[next_layer_idx]
            except IndexError:
                # The highest layer does not have a parent. Return empty list.
                return parents

            for other_doc in layered_docs:
                other_doc_layer = other_doc.get_layer()
                if other_doc_layer == parent_doc_layer:
                    # A document can have many labels but should only have one
                    # explicit label for the parentSelector.
                    parent_sel = doc.get_parent_selector()
                    parent_sel_key = list(parent_sel.keys())[0]
                    parent_sel_val = list(parent_sel.values())[0]
                    other_doc_labels = other_doc.get_labels()

                    if (parent_sel_key in other_doc_labels and
                        parent_sel_val == other_doc_labels[parent_sel_key]):
                        parents.append(other_doc)
            return parents

        for layer in layer_order:
            docs_by_layer = list(filter(
                (lambda x: x.get_layer() == layer), layered_docs))

            for doc in docs_by_layer:
                parents = _get_parents(doc)

                # Each document should have exactly one parent.
                if parents:
                    if not len(parents) == 1:
                        raise errors.IndeterminateDocumentParent(
                            document=doc, parents=parents)
                    doc.data.setdefault('parent', parents[0])
                # Unless the document is the topmost document in the
                # `layerOrder` of the LayeringPolicy, a parent document should
                # exist. Otherwise raise an exception.
                else:
                    if doc.get_layer() != layer_order[-1]:
                        raise errors.MissingDocumentParent(document=doc)

        return list(sorted(layered_docs,
                    key=lambda x: layer_order.index(x.get_layer())))
