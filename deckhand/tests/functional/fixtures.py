#
# Copyright 2015 Red Hat. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Fixtures used during Gabbi-based test runs."""

import os
from unittest import case
import yaml

from gabbi import fixture
from oslo_config import cfg
from oslo_policy import opts
from oslo_utils import fileutils
import six

from deckhand.conf import config
from deckhand.control import api

FAKE_CONF = cfg.CONF
TEST_APP = None


def setup_app():
    global TEST_APP

    if TEST_APP:
        return TEST_APP

    db_url = os.environ.get('PIFPAF_URL', "sqlite://").replace(
        "postgresql://", "postgresql+psycopg2://")
    if not db_url:
        raise case.SkipTest('No database connection configured')

    # Set up policy file.
    with open(
            os.path.abspath('etc/deckhand/policy.yaml.sample'), 'r') as stream:
        policy_yaml = stream.read().replace('#"deckhand', '"deckhand')
        policies = yaml.safe_load(policy_yaml)
    for action in policies:
        policies[action] = '@'

    content = yaml.safe_dump(policies)
    if six.PY3:
        content = content.encode('utf-8')
    tempfile = fileutils.write_to_tempfile(content=content,
                                           prefix='policy',
                                           suffix='.yaml')

    # Set up config options.
    paste_file = os.path.abspath('etc/deckhand/deckhand-paste.ini')
    FAKE_CONF([], project='deckhand', default_config_files=[
        os.path.abspath('etc/deckhand/deckhand.conf.sample'),
        paste_file
    ])

    config.register_opts(FAKE_CONF)
    opts.set_defaults(FAKE_CONF)
    FAKE_CONF.set_override("policy_file", tempfile,
                           group='oslo_policy')
    FAKE_CONF.set_override("allow_anonymous_access", True)
    FAKE_CONF.set_override('connection', db_url, group='database')

    TEST_APP = api.init_test_application(paste_file)
    return TEST_APP


class CORSConfigFixture(fixture.GabbiFixture):
    """Inject mock configuration for the CORS middleware."""

    def start_fixture(self):
        # Here we monkeypatch GroupAttr.__getattr__, necessary because the
        # paste.ini method of initializing this middleware creates its own
        # ConfigOpts instance, bypassing the regular config fixture.

        def _mock_getattr(instance, key):
            if key != 'allowed_origin':
                return self._original_call_method(instance, key)
            return "http://valid.example.com"

        self._original_call_method = cfg.ConfigOpts.GroupAttr.__getattr__
        cfg.ConfigOpts.GroupAttr.__getattr__ = _mock_getattr

    def stop_fixture(self):
        """Remove the monkeypatch."""
        cfg.ConfigOpts.GroupAttr.__getattr__ = self._original_call_method
