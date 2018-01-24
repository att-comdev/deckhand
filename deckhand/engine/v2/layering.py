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

from . import errors

__all__ = ['extract_layering_policy', 'find_parents', 'has_layering']


def apply_action(action, src, dest):
    raise NotImplementedError('Need to do this.')

    if action['method'] == 'merge':
        return _apply_merge(action['path'], src, dest)
    elif action['method'] == 'replace':
        return _apply_replace(action['path'], src, dest)
    elif action['method'] == 'delete':
        return _apply_delete(action['path'], dest)
    else:
        return [errors.UnknownLayeringMethod(action['method'])]


def _apply_merge(path, src, dest):
    return []


def _apply_replace(path, src, dest):
    return []


def _apply_delete(path, dest):
    return []


def extract_layering_policy(documents):
    layering_policies = []
    for d in documents:
        if d.schema == 'deckhand/LayeringPolicy/v1':
            layering_policies.append(d)
    if len(layering_policies) == 1:
        return layering_policies[0]
    elif len(layering_policies) > 1:
        raise errors.MultipleLayeringPolicies(layering_policies)
    else:
        raise errors.MissingLayeringPolicy


def find_parents(d, documents, layering_policy):
    selector = d.metadata.get('layeringDefinition', {}).get(
        'parentSelector', {})
    parents = []
    for candidate in documents:
        if (candidate.schema == d.schema
                and layer_preceeds(layering_policy, candidate.layer, d.layer)
                and candidate.has_labels(selector)):
            parents.append(candidate)
    return parents


def layer_preceeds(policy, a, b):
    if a == b:
        return False

    for layer in policy.data.get('layerOrder', []):
        if layer == a:
            return True

    return False


def has_layering(document):
    layering_def = document.metadata.get('layeringDefinition', {})
    return ('parentSelector' in layering_def and 'actions' in layering_def)
