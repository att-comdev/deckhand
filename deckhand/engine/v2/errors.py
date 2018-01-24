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

class EngineError(Exception):
    def __init__(self, *args, causes=None, **kwargs):
        super().__init__(*args, **kwargs)
        if causes is None:
            causes = []
        self.reject = any(c.reject for c in causes)
        self.causes = causes

    def __str__(self):
        return '%s(%s, reject=%s, causes=%s)' % (self.__class__.__name__,
                                                 self.args, self.reject,
                                                 self.causes)

    def __repr__(self):
        return str(self)


# XXX This is a temporary error while WIP
class WIP(EngineError):
    pass


class RenderError(EngineError):
    pass


class ConflictingDocumentsFound(EngineError):
    pass


class InternalError(EngineError):
    '''An InternalError always indicates a bug in the engine.'''


class MultipleStructuralOthers(InternalError):
    pass


class MultipleDataSchemas(InternalError):
    pass


class NoDataSchema(InternalError):
    pass


class RejectableError(EngineError):
    def __init__(self, *args, **kwargs):
        self.reject = True
        super().__init__(*args, **kwargs)


class StructuralValidationError(RejectableError):
    pass


class MetadataValidationError(RejectableError):
    pass


class DataValidationError(EngineError):
    pass


class JSONPathError(EngineError):
    pass


class JSONPathParseError(JSONPathError):
    pass


class JSONPathGetError(JSONPathError):
    pass


class JSONPathExtractError(JSONPathError):
    pass


class JSONPathInjectError(JSONPathError):
    pass


class LayeringError(EngineError):
    pass


class MissingLayeringPolicy(LayeringError):
    pass


class MultipleLayeringPolicies(LayeringError):
    pass


class TooManyParents(LayeringError):
    pass


class NoParents(LayeringError):
    pass


class UnknownLayeringMethod(LayeringError):
    pass


class SubstitutionError(EngineError):
    pass
