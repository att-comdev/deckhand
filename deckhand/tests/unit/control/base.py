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

import os
import yaml

from falcon import testing as falcon_testing

from deckhand import factories
from deckhand import service
from deckhand.tests.unit import base as test_base
from deckhand.tests.unit import fixtures


class BaseControllerTest(test_base.DeckhandWithDBTestCase,
                         falcon_testing.TestCase):
    """Base class for unit testing falcon controllers."""

    def setUp(self):
        super(BaseControllerTest, self).setUp()
        self.app = falcon_testing.TestClient(
            service.deckhand_app_factory(None))
        self.policy = self.useFixture(fixtures.RealPolicyFixture())
        # NOTE: allow_anonymous_access allows these unit tests to get around
        # Keystone authentication.
        self.useFixture(fixtures.ConfPatcher(allow_anonymous_access=True))

    def _read_data(self, file_name):
        # Reads data from a file in the resources directory
        dir_path = os.path.dirname(os.path.realpath(__file__))
        test_yaml_path = os.path.abspath(os.path.join(
            dir_path, os.pardir, 'resources', file_name + '.yaml'))

        with open(test_yaml_path, 'r') as yaml_file:
            yaml_data = yaml_file.read()
        self.data = yaml.safe_load(yaml_data)

    def _register_default_data_schema_document(self, schema_name=None,
                                               do_set_rules=True):
        """Registers default ``DataSchema`` document needed for document with
        ``schema``='example/Kind/v1.0' to be recognized by Deckhand.

        This should be called in the ``setUp`` method for a subclass so that
        the `DataSchema` is pre-registered before the tests that rely on it
        are called.
        """
        if not schema_name:
            schema_name = 'example/Kind/v1.0'

        if do_set_rules:
            rules = {'deckhand:create_cleartext_documents': '@'}
            self.policy.set_rules(rules)

        data_schema_factory = factories.DataSchemaFactory()
        payload = data_schema_factory.gen_test(schema_name, {})
        resp = self.app.simulate_put(
            '/api/v1.0/buckets/mop/documents',
            headers={'Content-Type': 'application/x-yaml'},
            body=yaml.safe_dump(payload))
        self.assertEqual(200, resp.status_code)
