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

import networkx
from networkx.algorithms.cycles import find_cycle
from networkx.algorithms.dag import topological_sort
from oslo_log import log as logging

from deckhand.engine import document_validation
from deckhand.engine import document_wrapper
from deckhand.engine import secrets_manager
from deckhand.engine import utils as engine_utils
from deckhand import errors
from deckhand import types
from deckhand import utils

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

    __slots__ = ('_documents_by_index', '_documents_by_labels',
                 '_documents_by_layer', '_layer_order', '_layering_policy',
                 '_parents', '_sorted_documents', 'secrets_substitution')

    _SUPPORTED_METHODS = (_MERGE_ACTION, _REPLACE_ACTION, _DELETE_ACTION) = (
        'merge', 'replace', 'delete')

    def _replace_older_parent_with_younger_parent(self, child, parent,
                                                  all_children):
        # If child has layer N, parent N+1, and current_parent N+2, then swap
        # parent with current_parent. In other words, if parent's layer is
        # closer to child's layer than current_parent's layer, then use parent.
        current_parent_index = self._parents.get((child.schema, child.name))
        current_parent = self._documents_by_index.get(
            current_parent_index, None)
        if current_parent:
            if (self._layer_order.index(parent.layer) >
                self._layer_order.index(current_parent.layer)):
                self._parents[(child.schema, child.name)] = \
                    (parent.schema, parent.name)
                all_children[child] -= 1
        else:
            self._parents.setdefault((child.schema, child.name),
                                     (parent.schema, parent.name))

    def _is_actual_child_document(self, document, potential_child):
        if document == potential_child:
            return False

        document_layer_idx = self._layer_order.index(document.layer)
        child_layer_idx = self._layer_order.index(potential_child.layer)

        parent_selector = potential_child.parent_selector
        labels = document.labels
        # Labels are key-value pairs which are unhashable, so use ``all``
        # instead.
        is_actual_child = all(
            labels.get(x) == y for x, y in parent_selector.items())

        if is_actual_child:
            # Documents with different `schema`s are never layered together,
            # so consider only documents with same schema as candidates.
            if potential_child.schema != document.schema:
                reason = ('Child has parentSelector which references parent, '
                          'but their `schema`s do not match.')
                LOG.error(reason)
                raise errors.InvalidDocumentParent(
                    parent_schema=document.schema, parent_name=document.name,
                    document_schema=potential_child.schema,
                    document_name=potential_child.name, reason=reason)

            # The highest order is 0, so the parent should be lower than the
            # child.
            if document_layer_idx >= child_layer_idx:
                reason = ('Child has parentSelector which references parent, '
                          'but the child layer %s must be lower than the '
                          'parent layer %s for layerOrder %s.' % (
                              potential_child.layer, document.layer,
                              ', '.join(self._layer_order)))
                LOG.error(reason)
                raise errors.InvalidDocumentParent(
                    parent_schema=document.schema, parent_name=document.name,
                    document_schema=potential_child.schema,
                    document_name=potential_child.name, reason=reason)

        return is_actual_child

    def _calc_document_children(self, document):
        potential_children = []
        for label_key, label_val in document.labels.items():
            _potential_children = self._documents_by_labels.get(
                (label_key, label_val), [])
            potential_children.extend(_potential_children)
        unique_potential_children = set(potential_children)

        for potential_child in unique_potential_children:
            if self._is_actual_child_document(document, potential_child):
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
        self._parents = {}

        for layer in self._layer_order:
            documents_in_layer = self._documents_by_layer.get(layer, [])
            for document in documents_in_layer:
                children = list(self._calc_document_children(document))

                if children:
                    all_children.update(children)

                for child in children:
                    self._replace_older_parent_with_younger_parent(
                        child, document, all_children)

        all_children_elements = list(all_children.elements())
        secondary_documents = []
        for layer, documents in self._documents_by_layer.items():
            if self._layer_order and layer != self._layer_order[0]:
                secondary_documents.extend(documents)

        for doc in secondary_documents:
            # Unless the document is the topmost document in the
            # `layerOrder` of the LayeringPolicy, it should be a child document
            # of another document.
            if doc not in all_children_elements:
                if doc.parent_selector:
                    LOG.debug(
                        'Could not find parent for document with name=%s, '
                        'schema=%s, layer=%s, parentSelector=%s.', doc.name,
                        doc.schema, doc.layer, doc.parent_selector)
            # If the document is a child document of more than 1 parent, then
            # the document has too many parents, which is a validation error.
            elif all_children[doc] > 1:
                LOG.info('%d parent documents were found for child document '
                         'with name=%s, schema=%s, layer=%s, parentSelector=%s'
                         '. Each document must have exactly 1 parent.',
                         all_children[doc], doc.name, doc.schema, doc.layer,
                         doc.parent_selector)
                raise errors.IndeterminateDocumentParent(document=doc)

    def _get_layering_order(self, layering_policy):
        # Pre-processing stage that removes empty layers from the
        # ``layerOrder`` in the layering policy.
        layer_order = list(layering_policy.layer_order)
        for layer in layer_order[:]:
            documents_by_layer = self._documents_by_layer.get(layer, [])
            if not documents_by_layer:
                LOG.info('%s is an empty layer with no documents. It will be '
                         'discarded from the layerOrder during the layering '
                         'process.', layer)
                layer_order.remove(layer)
        if not layer_order:
            LOG.info('Either the layerOrder in the LayeringPolicy was empty '
                     'to begin with or no document layers were found in the '
                     'layerOrder, causing it to become empty. No layering '
                     'will be performed.')
        return layer_order

    def _topologically_sort_documents(self, documents):
        """Topologically sorts the DAG formed from the documents' layering
        and substitution dependency chain.
        """
        documents_by_name = {}
        result = []

        g = networkx.DiGraph()
        for document in documents:
            document = document_wrapper.DocumentDict(document)
            documents_by_name.setdefault((document.schema, document.name),
                                         document)
            if document.parent_selector:
                parent = self._parents.get((document.schema, document.name))
                if parent:
                    g.add_edge((document.schema, document.name), parent)

            for sub in document.substitutions:
                g.add_edge((document.schema, document.name),
                           (sub['src']['schema'], sub['src']['name']))

        try:
            cycle = find_cycle(g)
        except networkx.exception.NetworkXNoCycle:
            pass
        else:
            LOG.error('Cannot determine substitution order as a dependency '
                      'cycle exists for the following documents: %s.', cycle)
            raise errors.SubstitutionDependencyCycle(cycle=cycle)

        sorted_documents = reversed(list(topological_sort(g)))

        for document in sorted_documents:
            if document in documents_by_name:
                result.append(documents_by_name.pop(document))
        for document in documents_by_name.values():
            result.append(document)

        return result

    def _pre_validate_documents(self, documents):
        LOG.debug('%s performing document pre-validation.',
                  self.__class__.__name__)
        validator = document_validation.DocumentValidation(
            documents, pre_validate=True)
        results = validator.validate_all()
        val_errors = []
        for result in results:
            val_errors.extend(
                [(e['schema'], e['name'], e['message'])
                    for e in result['errors']])
        if val_errors:
            for error in val_errors:
                LOG.error(
                    'Document [%s] %s failed with pre-validation error: %s.',
                    *error)
            raise errors.InvalidDocumentFormat(
                document_schema=', '.join(v[0] for v in val_errors),
                document_name=', '.join(v[1] for v in val_errors),
                errors=', '.join(v[2] for v in val_errors))

    def __init__(self, documents, substitution_sources=None, validate=True,
                 fail_on_missing_sub_src=True):
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
        :param validate: Whether to pre-validate documents using built-in
            schema validation. Skips over externally registered ``DataSchema``
            documents to avoid false positives. Default is True.
        :type validate: bool
        :param fail_on_missing_sub_src: Whether to fail on a missing
            substitution source. Default is True.
        :type fail_on_missing_sub_src: bool

        :raises LayeringPolicyNotFound: If no LayeringPolicy was found among
            list of ``documents``.
        :raises InvalidDocumentLayer: If document layer not found in layerOrder
            for provided LayeringPolicy.
        :raises InvalidDocumentParent: If child references parent but they
            don't have the same schema or their layers are incompatible.
        :raises IndeterminateDocumentParent: If more than one parent document
            was found for a document.
        """
        self._documents_by_layer = {}
        self._documents_by_labels = {}
        self._layering_policy = None
        self._sorted_documents = {}
        self._documents_by_index = {}

        # TODO(fmontei): Add a hook for post-validation too.
        if validate:
            self._pre_validate_documents(documents)

        layering_policies = list(
            filter(lambda x: x.get('schema').startswith(
                   types.LAYERING_POLICY_SCHEMA), documents))
        if layering_policies:
            self._layering_policy = document_wrapper.DocumentDict(
                layering_policies[0])
            if len(layering_policies) > 1:
                LOG.warning('More than one layering policy document was '
                            'passed in. Using the first one found: [%s] %s.',
                            self._layering_policy.schema,
                            self._layering_policy.name)

        if self._layering_policy is None:
            error_msg = (
                'No layering policy found in the system so could not render '
                'documents.')
            LOG.error(error_msg)
            raise errors.LayeringPolicyNotFound()

        for document in documents:
            document = document_wrapper.DocumentDict(document)
            self._documents_by_index.setdefault(
                (document.schema, document.name), document)
            if document.layer:
                if document.layer not in self._layering_policy.layer_order:
                    LOG.error('Document layer %s for document [%s] %s not '
                              'in layerOrder: %s.', document.layer,
                              document.schema, document.name,
                              self._layering_policy.layer_order)
                    raise errors.InvalidDocumentLayer(
                        document_layer=document.layer,
                        document_schema=document.schema,
                        document_name=document.name,
                        layer_order=', '.join(
                            self._layering_policy.layer_order),
                        layering_policy_name=self._layering_policy.name)
                self._documents_by_layer.setdefault(document.layer, [])
                self._documents_by_layer[document.layer].append(document)
            if document.parent_selector:
                for label_key, label_val in document.parent_selector.items():
                    self._documents_by_labels.setdefault(
                        (label_key, label_val), [])
                    self._documents_by_labels[
                        (label_key, label_val)].append(document)

        self._layer_order = self._get_layering_order(self._layering_policy)
        self._calc_all_document_children()

        self.secrets_substitution = secrets_manager.SecretsSubstitution(
            substitution_sources or [],
            fail_on_missing_sub_src=fail_on_missing_sub_src)

        self._sorted_documents = self._topologically_sort_documents(documents)

        del self._documents_by_layer
        del self._documents_by_labels

    def _apply_action(self, action, child_data, overall_data):
        """Apply actions to each layer that is rendered.

        Supported actions include:

            * ``merge`` - a "deep" merge that layers new and modified data onto
              existing data
            * ``replace`` - overwrite data at the specified path and replace it
              with the data given in this document
            * ``delete`` - remove the data at the specified path

        :raises UnsupportedActionMethod: If the layering action isn't found
            among ``self.SUPPORTED_METHODS``.
        :raises MissingDocumentKey: If a layering action path isn't found
            in the child document.
        """
        method = action['method']
        if method not in self._SUPPORTED_METHODS:
            raise errors.UnsupportedActionMethod(
                action=action, document=child_data)

        # Use copy to prevent these data from being updated referentially.
        overall_data = copy.deepcopy(overall_data)
        child_data = copy.deepcopy(child_data)

        action_path = action['path']
        if action_path.startswith('.data'):
            action_path = action_path[5:]

        if method == self._DELETE_ACTION:
            if action_path == '.':
                overall_data.data = {}
            else:
                from_child = utils.jsonpath_parse(overall_data.data,
                                                  action_path)
                if from_child is None:
                    raise errors.MissingDocumentKey(
                        child_schema=child_data.schema,
                        child_name=child_data.name,
                        parent_schema=overall_data.schema,
                        parent_name=overall_data.name,
                        action=action)

                engine_utils.deep_delete(from_child, overall_data.data, None)

        elif method == self._MERGE_ACTION:
            from_parent = utils.jsonpath_parse(overall_data.data, action_path)
            from_child = utils.jsonpath_parse(child_data.data, action_path)

            if from_child is None:
                raise errors.MissingDocumentKey(
                    child_schema=child_data.schema,
                    child_name=child_data.name,
                    parent_schema=overall_data.schema,
                    parent_name=overall_data.name,
                    action=action)

            if (isinstance(from_parent, dict)
                    and isinstance(from_child, dict)):
                engine_utils.deep_merge(from_parent, from_child)

            if from_parent is not None:
                overall_data.data = utils.jsonpath_replace(
                    overall_data.data, from_parent, action_path)
            else:
                overall_data.data = utils.jsonpath_replace(
                    overall_data.data, from_child, action_path)
        elif method == self._REPLACE_ACTION:
            from_child = utils.jsonpath_parse(child_data.data, action_path)

            if from_child is None:
                raise errors.MissingDocumentKey(
                    child_schema=child_data.schema,
                    child_name=child_data.name,
                    parent_schema=overall_data.schema,
                    parent_name=overall_data.name,
                    action=action)

            overall_data.data = utils.jsonpath_replace(
                overall_data.data, from_child, action_path)

        return overall_data

    def render(self):
        """Perform layering on the list of documents passed to ``__init__``.

        Each concrete document will undergo layering according to the actions
        defined by its ``metadata.layeringDefinition``. Documents are layered
        with their parents. A parent document's ``schema`` must match that of
        the child, and its ``metadata.labels`` must much the child's
        ``metadata.layeringDefinition.parentSelector``.

        :returns: The list of concrete rendered documents.
        :rtype: List[dict]

        :raises UnsupportedActionMethod: If the layering action isn't found
            among ``self.SUPPORTED_METHODS``.
        :raises MissingDocumentKey: If a layering action path isn't found
            in both the parent and child documents being layered together.
        """
        for doc in self._sorted_documents:

            if doc.parent_selector:
                parent_meta = self._parents.get((doc.schema, doc.name))

                if parent_meta:
                    parent = self._documents_by_index[parent_meta]

                    if doc.actions:
                        rendered_data = parent
                        for action in doc.actions:
                            LOG.debug('Applying action %s to document with '
                                      'name=%s, schema=%s, layer=%s.', action,
                                      doc.name, doc.schema, doc.layer)
                            rendered_data = self._apply_action(
                                action, doc, rendered_data)
                        if not doc.is_abstract:
                            doc.data = rendered_data.data
                        self.secrets_substitution.update_substitution_sources(
                            doc.schema, doc.name, rendered_data.data)
                        self._documents_by_index[(doc.schema, doc.name)] = (
                            rendered_data)
                    else:
                        LOG.info('Skipped layering for document [%s] %s which '
                                 'has a parent [%s] %s, but no associated '
                                 'layering actions.', doc.schema, doc.name,
                                 parent.schema, parent.name)

            # Perform substitutions on abstract data for child documents that
            # inherit from it, but only update the document's data if concrete.
            if doc.substitutions:
                substituted_data = list(
                    self.secrets_substitution.substitute_all(doc))
                if substituted_data:
                    rendered_data = substituted_data[0]
                    # Update the actual document data if concrete.
                    if not doc.is_abstract:
                        doc.data = rendered_data.data
                    self.secrets_substitution.update_substitution_sources(
                        doc.schema, doc.name, rendered_data.data)
                    self._documents_by_index[(doc.schema, doc.name)] = (
                        rendered_data)

        # Return only concrete documents.
        return [d for d in self._sorted_documents if d.is_abstract is False]

    @property
    def documents(self):
        return self._sorted_documents