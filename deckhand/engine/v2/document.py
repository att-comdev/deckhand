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

import abc

__all__ = ['CompleteDocument', 'Document']


class Document(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def as_dict(self):
        pass

    @property
    @abc.abstractmethod
    def as_dict_for_root_validation(self):
        pass

    @property
    @abc.abstractmethod
    def data(self):
        pass

    @property
    def full_name(self):
        return '%s/%s' % (self.schema, self.name)

    @property
    def is_control(self):
        return self.metadata.get('schema') == 'metadata/Control/v1'

    def __eq__(self, other):
        return self.full_name == other.full_name

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return str(self)

    @property
    def substitutions(self):
        return self.metadata.get('substitutions', [])

    @property
    def schema(self):
        return self.as_dict_for_root_validation.get('schema')

    @property
    def metadata(self):
        return self.as_dict_for_root_validation.get('metadata', {})

    @property
    def name(self):
        return self.metadata.get('name')

    @property
    def abstract(self):
        return self.metadata.get('layeringDefinition', {}).get(
            'abstract', False)

    @property
    def layer(self):
        return self.metadata.get('layeringDefinition', {}).get('layer')

    def has_labels(self, selector):
        labels = self.metadata.get('labels', {})
        for skey, sval in selector.items():
            if labels.get(skey) != sval:
                return False
        return True


class CompleteDocument(Document):
    def __init__(self, dict_):
        self.dict_ = dict_

    @property
    def as_dict(self):
        return self.dict_

    @property
    def as_dict_for_root_validation(self):
        return self.dict_

    @property
    def data(self):
        return self.dict_.get('data', {})
