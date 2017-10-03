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

from falcon import testing as falcon_testing

from deckhand.control import api
from deckhand.tests.unit import base as test_base
from deckhand.tests.unit import policy_fixture


class BaseControllerTest(test_base.DeckhandWithDBTestCase,
                         falcon_testing.TestCase):
    """Base class for unit testing falcon controllers."""

    def setUp(self):
        super(BaseControllerTest, self).setUp()
        self.app = falcon_testing.TestClient(api.start_api())
        self.policy = self.useFixture(policy_fixture.RealPolicyFixture())
        # Override default rules in the temporary policy file that is created
        # in ``RealPolicyFixture`` with "@" which allows anyone to perform an
        # action.
        self.policy.set_rules('@')


class BaseAdminControllerTest(test_base.DeckhandWithDBTestCase,
                              falcon_testing.TestCase):
    """Base admin class for unit testing falcon controllers.

    Only users with admin credentials can execute any actions. Useful for
    negative testing RBAC.
    """

    def setUp(self):
        super(BaseAdminControllerTest, self).setUp()
        self.app = falcon_testing.TestClient(api.start_api())
        self.policy = self.useFixture(policy_fixture.RealPolicyFixture())
