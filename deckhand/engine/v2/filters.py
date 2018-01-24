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


class Filter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def matches(self, document) -> bool:
        pass

    def apply(self, documents):
        result = []
        for d in documents:
            if self.matches(d):
                result.append(d)
        return result


class Null(Filter):
    def matches(self, document):
        return True


class And(Filter):
    def __init__(self, filters):
        self.filters = filters

    def matches(self, document):
        return all(f.maches(document) for f in self.filters)


class Or(Filter):
    def __init__(self, filters):
        self.filters = filters

    def matches(self, document):
        return any(f.maches(document) for f in self.filters)


class PathEquals(Filter):
    def __init__(self, *, path, value):
        self.path = path
        self.value = value

    def matches(self, document):
        # XXX implement this
        return False
