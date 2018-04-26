# Copyright 2018 AT&T Intellectual Property.  All other rights reserved.
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

"""Fixtures for Deckhand tests."""
from __future__ import absolute_import

import os
import time

import fixtures

_TRUE_VALUES = ('True', 'true', '1', 'yes')


class TestTimeoutFixture(fixtures.Fixture):
    """Ensure that a test is executed within a timeout limit after which the
    test will fail.
    """
    def setUp(self):
        super(TestTimeoutFixture, self).setUp()
        self.timeout = int(os.environ.get('DECKHAND_PERFORMANCE_TIMEOUT', 10))
        self.start = time.time()

    def cleanUp(self):
        super(TestTimeoutFixture, self).cleanUp()
        if os.environ.get('DECKHAND_PERFORMANCE_TESTING') in _TRUE_VALUES:
            if time.time() > self.start + self.timeout:
                raise RuntimeError(
                    'Test failed to execute within the allowed timeout: %ds'
                    % self.timeout)
