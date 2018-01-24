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

from . import compute_graph, errors, filters, operations, validation
import logging
import networkx

LOG = logging.getLogger(__name__)


class Engine:
    def __init__(self, documents, *, force_own_schemas=True):
        # XXX Need to check for duplicate/conflicting docs
        if force_own_schemas:
            documents = _force_own_schemas(documents)
        self.documents = documents
        self.workspace = compute_graph.initialize_workspace(documents)
        self.graph = compute_graph.build_graph(documents)
        self._has_cycles = None

    @property
    def has_cycles(self):
        if self._has_cycles is None:
            self._has_cycles = False
            for c in networkx.cycles.simple_cycles(self.graph):
                LOG.warning('Found cycle: %s', c)
                self._has_cycles = True
                break

        return self._has_cycles

    def render(self, filter_=None):
        nodes = self._select(filter_)
        render_errors = []
        for node in nodes:
            node_errors = self._render_node(node)
            render_errors.extend(node_errors)

        if not render_errors:
            return [self.workspace[n] for n in nodes]
        else:
            raise errors.RenderError(causes=render_errors)

    def _render_node(self, node):
        '''This function does the heavy lifting of managing computation flow.'''
        ancestors = networkx.ancestors(self.graph, node)
        ancestors.add(node)
        g = self.graph.subgraph(ancestors)
        errors = []
        for op_node in networkx.topological_sort(g):
            blocked = networkx.get_node_attributes(self.graph, 'blocked').get(
                node, False)
            if not blocked:
                op_errors = self._execute_operation(op_node)
                if op_errors:
                    LOG.debug('Got %d errors from %s', len(op_errors), op_node)
                    errors.extend(op_errors)
                    self._block_descendants(op_node)

        return errors

    def _block_descendants(self, node):
        descendants = list(networkx.descendants(self.graph, node))
        LOG.debug('Blocking descendants for %s: %s', node, descendants)
        for d in descendants:
            networkx.set_node_attributes(self.graph, {d: True}, 'blocked')

    def _execute_operation(self, node):
        op_name, schema, name = _split(node)
        op_class = operations.OPERATIONS[op_name]
        others = []
        this_doc = None
        for pred in self.graph.predecessors(node):
            _, pred_schema, pred_name = _split(pred)
            if (pred_schema == schema and pred_name == name):
                this_doc = self.workspace[pred]
            else:
                others.append(self.workspace[pred])

        op = op_class(node, this_doc, others)
        return op.execute(self.workspace)

    def _select(self, filter_=None):
        if filter_ is None:
            filter_ = filters.Null()
        selected_documents = filter_.apply(self.documents)
        return [compute_graph._dn(d, 'validate') for d in selected_documents]

    def find_missing_documents(self, filter_=None):
        nodes = self._select(filter_)
        missing = set()
        for node in nodes:
            ancestors = networkx.ancestors(self.graph, node)
            ancestors.add(node)
            g = self.graph.subgraph(ancestors)
            for key, preds in g.pred.items():
                if not preds and key not in self.workspace:
                    _op, schema, name = _split(key)
                    missing.add((schema, name))

        return missing


def _is_source(key):
    return key.startswith('source/')


def _split(node):
    parts = node.split('/')
    op = parts[0]
    schema = '/'.join(parts[1:4])
    name = '/'.join(parts[4:])
    return op, schema, name


def _force_own_schemas(documents):
    keep = validation.get_owned_schemas()
    LOG.debug('keep: %s', keep)
    for d in documents:
        if (d.schema != 'deckhand/DataSchema/v1'
                or not d.name.startswith('deckhand/')):
            keep.append(d)

    return keep
