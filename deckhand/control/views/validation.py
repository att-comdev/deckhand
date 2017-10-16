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

from deckhand.control import common
from deckhand import types
from deckhand import utils


class ViewBuilder(common.ViewBuilder):
    """Model validation API responses as a python dictionary."""

    _collection_name = 'validations'

    def list(self, validations):
        return [self.show(v) for v in validations]

    def show(self, validation):
        default_validator = {'name': 'deckhand', 'version': '1.0'}
        return {
            'status': validation.get('status'),
            'validator': validation.get('validator', default_validator)
        }
