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


class ViewBuilder(common.ViewBuilder):
    """Model revision tag API responses as a python dictionary."""

    @classmethod
    def list(cls, tags):
        resp = {}
        for tag in tags:
            resp.update(cls._show(tag))
        return resp

    @classmethod
    def show(cls, tag):
        return cls._show(tag)

    @classmethod
    def _show(cls, tag):
        return {
            tag['tag']: tag.get('data', {})
        }
