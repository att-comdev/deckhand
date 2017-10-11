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

from deckhand.control import api


def start_deckhand():
    return api.init_application()


# Initialization compatible with PasteDeploy
def paste_start_deckhand(global_conf, **kwargs):
    return deckhand_callable


# Callable to be used by uwsgi.
deckhand_callable = start_deckhand()
