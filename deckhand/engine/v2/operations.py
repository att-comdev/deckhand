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

from . import errors, layering, substitution, validation
from .document import CompleteDocument
import abc
import copy
import logging

LOG = logging.getLogger(__name__)


class Operation(metaclass=abc.ABCMeta):
    def __init__(self, name, document, others):
        self.name = name
        self.document = document
        self.others = others

        LOG.debug('%s: %s (%s) %s', self.__class__.__name__, self.name,
                  self.document, self.others)

    @abc.abstractmethod
    def execute(self, workspace):
        pass


class NoOperation(Operation):
    def execute(self, workspace):
        if self.others:
            LOG.warn('Found unexpected "others" for NoOperation %s', self.name)
        return []


class CopyOperation(Operation):
    def execute(self, workspace):
        if self.others:
            LOG.warn('Found unexpected "others" for CopyOperation %s',
                     self.name)
        workspace[self.name] = self.document
        return []


class ValidateStructureOperation(Operation):
    def execute(self, workspace):
        if self.others:
            if len(self.others) > 1:
                return [
                    errors.MultipleStructuralOthers(
                        [d.full_name for d in self.others])
                ]
            layering_policy = self.others[0]
        else:
            layering_policy = None

        workspace[self.name] = self.document
        return validation.structural(self.document, layering_policy)


class LayerOperation(Operation):
    def execute(self, workspace):
        LOG.debug('Executing layering %s (%s) %s', self.name, self.document,
                  self.others)
        if len(self.others) == 1:
            parent = self.others[0]
            data = {
                'schema': self.document.schema,
                'metadata': self.document.metadata,
                'data': copy.deepcopy(parent.data),
            }
            layer_errors = []
            for action in self.document.metadata.get('layeringDefinition',
                                                     {}).get('actions', []):
                action_errors = layering.apply_action(action,
                                                      self.document.data, data)
                if action_errors:
                    layer_errors.extend(action_errors)
                    break

            if not layer_errors:
                workspace[self.name] = CompleteDocument(data)
                return []
            else:
                return [errors.LayeringError(causes=layer_errors)]

        elif len(self.others) >= 1:
            return [errors.TooManyParents(len(self.others))]
        else:
            return [errors.NoParents()]


class SubstituteOperation(Operation):
    def execute(self, workspace):
        doc, sub_errors = substitution.apply(self.document, self.others)
        if not sub_errors:
            workspace[self.name] = doc
            return []
        else:
            return [errors.SubstitutionError(causes=sub_errors)]


class ValidateDataOperation(Operation):
    def execute(self, workspace):
        if (self.document.schema == 'deckhand/DataSchema/v1'
                and self.document.name == 'deckhand/DataSchema/v1'):
            # NOTE(mark-burnett): DataSchema is a special case that uses itself
            # for validation.
            data_schema = self.document
        elif self.others:
            if len(self.others) > 1:
                return [
                    errors.MultipleDataSchemas(
                        (self.name, [d.full_name for d in self.others]))
                ]
            data_schema = self.others[0]
        else:
            return [errors.NoDataSchema(self.name)]

        validation_errors = validation.validate_data(self.document,
                                                     data_schema)
        if not validation_errors:
            workspace[self.name] = self.document
        return validation_errors


OPERATIONS = {
    'source': NoOperation,
    'structural': ValidateStructureOperation,
    'layer': LayerOperation,
    'substitute': SubstituteOperation,
    'render': CopyOperation,
    'validate': ValidateDataOperation,
}
