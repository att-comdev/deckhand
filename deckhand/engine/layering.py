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

from oslo_log import log as logging

from deckhand.engine import document_wrapper
from deckhand.engine import secrets_manager
from deckhand.engine import utils
from deckhand import errors
from deckhand import types

LOG = logging.getLogger(__name__)


class DocumentLayering(object):
    """Class responsible for handling document layering.

    Layering is controlled in two places:

    1. The ``LayeringPolicy`` control document, which defines the valid layers
       and their order of precedence.
    2. In the ``metadata.layeringDefinition`` section of normal
       (``metadata.schema=metadata/Document/v1.0``) documents.

    .. note::

        Only documents with the same ``schema`` are allowed to be layered
        together into a fully rendered document.
    """

    SUPPORTED_METHODS = ('merge', 'replace', 'delete')

    def _is_child_document(self, document, potential_child, target_layer):
        # Documents with different schemas are never layered together,
        # so consider only documents with same schema as candidates.
        is_potential_child = (
            potential_child.layer == target_layer and
            potential_child.schema == document.schema
        )
        if is_potential_child:
            parent_selector = potential_child.parent_selector
            labels = document.labels
            if not isinstance(parent_selector, list):
                parent_selector = [parent_selector]
            if not isinstance(labels, list):
                labels = [labels]
            # Labels are key-value pairs which are unhashable, so use ``all``
            # instead.
            return all(x in labels for x in parent_selector)
        return False

    def _calc_document_children(self, document):
        try:
            document_layer_idx = self._layer_order.index(document.layer)
            child_layer = self._layer_order[document_layer_idx + 1]
        except IndexError:
            # The lowest layer has been reached, so no children. Return
            # empty list.
            return
        for potential_child in self._documents_to_layer:
            # Documents with different schemas are never layered together,
            # so consider only documents with same schema as candidates.
            if self._is_child_document(document, potential_child, child_layer):
                yield potential_child

    def _calc_all_document_children(self):
        """Determine each document's children.

        For each document, attempts to find the document's children. Adds a new
        key called "children" to the document's dictionary.

        .. note::

            A document should only have exactly one parent.

            If a document does not have a parent, then its layer must be
            the topmost layer defined by the ``layerOrder``.

        :returns: Ordered list of documents that need to be layered. Each
            document contains a "children" property in addition to original
            data. List of documents returned is ordered from highest to lowest
            layer.
        :rtype: List[:class:`DocumentDict`]
        :raises IndeterminateDocumentParent: If more than one parent document
            was found for a document.
        """
        # ``all_children`` is a counter utility for verifying that each
        # document has exactly one parent.
        all_children = collections.Counter()
        # Mapping of (doc.name, doc.metadata.name) => children, where children
        # are the documents whose `parentSelector` references the doc.
        self._children = {}
        self._parentless_documents = []

        for layer in self._layer_order:
            documents_in_layer = self._document_layer_map.get(layer, [])
            for document in documents_in_layer:
                children = list(self._calc_document_children(document))
                if children:
                    all_children.update(children)
                    self._children.setdefault(
                        (document.name, document.schema), children)

        all_children_elements = list(all_children.elements())
        secondary_documents = []
        for layer, documents in self._document_layer_map.items():
            if layer != self._layer_order[0]:
                secondary_documents.extend(documents)

        for doc in secondary_documents:
            # Unless the document is the topmost document in the
            # `layerOrder` of the LayeringPolicy, it should be a child document
            # of another document.
            if doc not in all_children_elements:
                LOG.info('Could not find parent for document with name=%s, '
                         'schema=%s, layer=%s, parentSelector=%s.',
                         doc.name, doc.schema, doc.layer, doc.parent_selector)
                self._parentless_documents.append(doc)
            # If the document is a child document of more than 1 parent, then
            # the document has too many parents, which is a validation error.
            elif all_children[doc] > 1:
                LOG.info('%d parent documents were found for child document '
                         'with name=%s, schema=%s, layer=%s, parentSelector=%s'
                         '. Each document must have exactly 1 parent.',
                         all_children[doc], doc.name, doc.schema, doc.layer,
                         doc.parent_selector)
                raise errors.IndeterminateDocumentParent(document=doc)

    def _extract_layering_policy(self, documents):
        for doc in documents:
            if doc['schema'].startswith(types.LAYERING_POLICY_SCHEMA):
                layering_policy = doc
                return (
                    document_wrapper.DocumentDict(layering_policy),
                    [document_wrapper.DocumentDict(d) for d in documents
                     if d is not layering_policy]
                )
        return None, [document_wrapper.DocumentDict(d) for d in documents]

    def __init__(self, documents, substitution_sources=None):
        """Contructor for ``DocumentLayering``.

        :param layering_policy: The document with schema
            ``deckhand/LayeringPolicy`` needed for layering.
        :param documents: List of all other documents to be layered together
            in accordance with the ``layerOrder`` defined by the
            LayeringPolicy document.
        :type documents: List[dict]
        :param substitution_sources: List of documents that are potential
            sources for substitution. Should only include concrete documents.
        :type substitution_sources: List[dict]
        """
        self._layering_policy, self._documents = self._extract_layering_policy(
            documents)
        if self._layering_policy is None:
            error_msg = (
                'No layering policy found in the system so could not reder '
                'documents.')
            LOG.error(error_msg)
            raise errors.LayeringPolicyNotFound()
        self._layer_order = list(self._layering_policy['data']['layerOrder'])

        self._documents_to_layer = []
        self._document_layer_map = {}
        for document in self._documents:
            if document.layering_definition:
                self._documents_to_layer.append(document)
            self._document_layer_map.setdefault(document.layer, [])
            self._document_layer_map[document.layer].append(document)

        self._calc_all_document_children()
        self._substitution_sources = substitution_sources or []

    def _apply_action(self, action, child_data, overall_data):
        """Apply actions to each layer that is rendered.

        Supported actions include:

            * `merge` - a "deep" merge that layers new and modified data onto
              existing data
            * `replace` - overwrite data at the specified path and replace it
              with the data given in this document
            * `delete` - remove the data at the specified path
        """
        method = action['method']
        if method not in self.SUPPORTED_METHODS:
            raise errors.UnsupportedActionMethod(
                action=action, document=child_data)

        # Use copy prevent these data from being updated referentially.
        overall_data = copy.deepcopy(overall_data)
        child_data = copy.deepcopy(child_data)
        rendered_data = overall_data

        # Remove empty string paths and ensure that "data" is always present.
        path = action['path'].split('.')
        path = [p for p in path if p != '']
        path.insert(0, 'data')
        last_key = 'data' if not path[-1] else path[-1]

        for attr in path:
            if attr == path[-1]:
                break
            rendered_data = rendered_data.get(attr)
            child_data = child_data.get(attr)

        if method == 'delete':
            # If the entire document is passed (i.e. the dict including
            # metadata, data, schema, etc.) then reset data to an empty dict.
            if last_key == 'data':
                rendered_data['data'] = {}
            elif last_key in rendered_data:
                del rendered_data[last_key]
            elif last_key not in rendered_data:
                # If the key does not exist in `rendered_data`, this is a
                # validation error.
                raise errors.MissingDocumentKey(
                    child=child_data, parent=rendered_data, key=last_key)
        elif method == 'merge':
            if last_key in rendered_data and last_key in child_data:
                # If both entries are dictionaries, do a deep merge. Otherwise
                # do a simple merge.
                if (isinstance(rendered_data[last_key], dict)
                    and isinstance(child_data[last_key], dict)):
                    utils.deep_merge(
                        rendered_data[last_key], child_data[last_key])
                else:
                    rendered_data.setdefault(last_key, child_data[last_key])
            elif last_key in child_data:
                rendered_data.setdefault(last_key, child_data[last_key])
            else:
                # If the key does not exist in the child document, this is a
                # validation error.
                raise errors.MissingDocumentKey(
                    child=child_data, parent=rendered_data, key=last_key)
        elif method == 'replace':
            if last_key in rendered_data and last_key in child_data:
                rendered_data[last_key] = child_data[last_key]
            elif last_key in child_data:
                rendered_data.setdefault(last_key, child_data[last_key])
            elif last_key not in child_data:
                # If the key does not exist in the child document, this is a
                # validation error.
                raise errors.MissingDocumentKey(
                    child=child_data, parent=rendered_data, key=last_key)

        return overall_data

    def _get_children(self, document):
        """Recursively retrieve all children.

        Used in the layering module when calculating children for each
        document.

        :returns: List of nested children.
        :rtype: Generator[:class:`DocumentDict`]
        """
        for child in self._children.get((document.name, document.schema), []):
            yield child
            grandchildren = self._get_children(child)
            for grandchild in grandchildren:
                yield grandchild

    def _apply_substitutions(self, document):
        try:
            secrets_substitution = secrets_manager.SecretsSubstitution(
                document, self._substitution_sources)
            return secrets_substitution.substitute_all()
        except errors.SubstitutionDependencyNotFound:
            LOG.error('Failed to render the documents because a secret '
                      'document could not be found.')

    def render(self):
        """Perform layering on the list of documents passed to ``__init__``.

        Each concrete document will undergo layering according to the actions
        defined by its ``metadata.layeringDefinition``. Documents are layered
        with their parents. A parent document's ``schema`` must match that of
        the child, and its ``metadata.labels`` must much the child's
        ``metadata.layeringDefinition.parentSelector``.

        :returns: The list of rendered documents (does not include layering
            policy document).
        :rtype: list[dict]
        """
        # ``rendered_data_by_layer`` tracks the set of changes across all
        # actions across each layer for a specific document.
        rendered_data_by_layer = document_wrapper.DocumentDict()

        # NOTE(fmontei): ``global_docs`` represents the topmost documents in
        # the system. It should probably be impossible for more than 1
        # top-level doc to exist, but handle multiple for now.
        global_docs = [doc for doc in self._documents_to_layer
                       if doc.layer == self._layer_order[0]]

        for doc in global_docs:
            layer_idx = self._layer_order.index(doc.layer)
            if doc.substitutions:
                substituted_data = self._apply_substitutions(doc)
                if substituted_data:
                    rendered_data_by_layer[layer_idx] = substituted_data[0]
            else:
                rendered_data_by_layer[layer_idx] = doc

            # Keep iterating as long as a child exists.
            for child in self._get_children(doc):
                # Retrieve the most up-to-date rendered_data (by
                # referencing the child's parent's data).
                child_layer_idx = self._layer_order.index(child.layer)
                rendered_data = rendered_data_by_layer[child_layer_idx - 1]

                # Apply each action to the current document.
                for action in child.actions:
                    LOG.debug('Applying action %s to child document with '
                              'name=%s, schema=%s, layer=%s.', action,
                              child.name, child.schema, child.layer)
                    rendered_data = self._apply_action(
                        action, child, rendered_data)

                # Update the actual document data if concrete.
                if not child.is_abstract:
                    if child.substitutions:
                        rendered_data.substitutions = child.substitutions
                        substituted_data = self._apply_substitutions(
                            rendered_data)
                        if substituted_data:
                            rendered_data = substituted_data[0]
                    child_index = self._documents_to_layer.index(child)
                    self._documents_to_layer[child_index].data = (
                        rendered_data.data)

                # Update ``rendered_data_by_layer`` for this layer so that
                # children in deeper layers can reference the most up-to-date
                # changes.
                rendered_data_by_layer[child_layer_idx] = rendered_data

        # Handle edge case for parentless documents that require substitution.
        # If a document has no parent, then the for loop above doesn't iterate
        # over the parentless document, so substitution must be done here for
        # parentless documents.
        for doc in self._parentless_documents:
            if not doc.is_abstract and doc.substitutions:
                substituted_data = self._apply_substitutions(doc)
                if substituted_data:
                    doc = substituted_data[0]

        return self._documents_to_layer + [self._layering_policy]
