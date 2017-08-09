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

import copy
import os
import yaml

import mock
import six

from deckhand.engine import secrets
from deckhand import errors
from deckhand.tests import factories
from deckhand.tests.unit import base


class TestSecretsResource(base.DeckhandWithDBTestCase):


    def setUp(self):
        super(TestSecretsResource, self).setUp()
        self.mock_barbican_driver = mock.patch.object(
            secrets.SecretsResource, 'barbican_driver', autospec=True).start()
        self.secrets_resource = secrets.SecretsResource()
        self.factory = factories.DocumentSecretFactory()

    def test_create_cleartext_certificate(self):
        certificate_doc = self.factory.gen('Certificate', 'cleartext')
        self.secrets_resource.post(certificate_doc)
