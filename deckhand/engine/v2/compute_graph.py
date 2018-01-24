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

from . import layering
import logging
import networkx

__all__ = ['build_graph', 'initialize_workspace']

LOG = logging.getLogger(__name__)


def build_graph(documents):
    '''Builds the internal directed graph used for computation.
    Each node specifies a particular operation to perform on the data.

    This is one of the more complex parts of the engine.  Once this graph is
    constructed, the operations proceed in relatively straightforward fashion.

    Operations occur in the following order:

        1. source - A placeholder for the provided data.
        2. structural - Perform structural and metadata validation.
        3. layer - Perform layering (optional).
        4. substitute - Perform substitution (optional).
        5. render - A placeholder for the final data, though it may be
           abstract.
        6. validate - Perform data validation.  Data is not concrete and
           queriable by users.
    '''
    layering_policy = layering.extract_layering_policy(documents)
    g = networkx.DiGraph()
    for d in documents:
        structural_node = _dn(d, 'structural')
        g.add_edge(_dn(d, 'source'), structural_node)
        if not d.is_control:
            g.add_edge(_dn(layering_policy, 'validate'), structural_node)
        prev = structural_node

        if layering.has_layering(d):
            layer_node = _dn(d, 'layer')
            g.add_edge(prev, layer_node)
            prev = layer_node

            parents = layering.find_parents(d, documents, layering_policy)
            if parents:
                for parent in parents:
                    g.add_edge(_dn(parent, 'render'), layer_node)
            else:
                g.add_edge(_missing_layer_parent(d), layer_node)

        if d.substitutions:
            sub_layer = _dn(d, 'substitute')
            g.add_edge(prev, sub_layer)
            prev = sub_layer

            for sub in d.substitutions:
                g.add_edge(_sub_node(sub), sub_layer)

        render_node = _dn(d, 'render')
        g.add_edge(prev, render_node)
        prev = render_node

        if not d.abstract:
            validate_node = _dn(d, 'validate')
            g.add_edge(prev, validate_node)
            g.add_edge(_schema_node(d), validate_node)

    return g


def initialize_workspace(documents):
    return {_dn(d, 'source'): d for d in documents}


def _dn(d, op):
    '''Returns the node tag for a document of given operation'''
    return '%s/%s/%s' % (op, d.schema, d.name)


def _sub_node(sub):
    src = sub.get('src', {})
    # TODO(mark-burnett): Need to handle this mapping better, since UNSPECIFIED
    # is an illegal name now.
    return 'validate/%s/%s' % (src.get('schema', 'UNSPECIFIED'),
                               src.get('name', 'UNSPECIFIED'))


def _missing_layer_parent(d):
    # TODO(mark-burnett): Need to handle this mapping better, since MISSING is
    # an illegal name now.
    return 'render/%s/MISSING' % d.schema


def _schema_node(d):
    return 'render/deckhand/DataSchema/v1/%s' % d.schema
