<<<<<<< 277c22816748669916dd7256f9260503955ee773
# Copyright 2017 AT&T Intellectual Property.  All other rights reserved.
#
=======
>>>>>>> Add layering policy pre-validation schema
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
<<<<<<< 277c22816748669916dd7256f9260503955ee773
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
=======
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
>>>>>>> Add layering policy pre-validation schema
# See the License for the specific language governing permissions and
# limitations under the License.

import fixtures
from oslo_config import cfg
from oslo_log import log as logging
import testtools

<<<<<<< 277c22816748669916dd7256f9260503955ee773
from deckhand.conf import config
from deckhand.db.sqlalchemy import api as db_api
from deckhand.db.sqlalchemy import models as db_models
=======
# from murano.db import api as db_api
>>>>>>> Add layering policy pre-validation schema

CONF = cfg.CONF
logging.register_options(CONF)
logging.setup(CONF, 'deckhand')


class DeckhandTestCase(testtools.TestCase):

    def setUp(self):
        super(DeckhandTestCase, self).setUp()
        self.useFixture(fixtures.FakeLogger('deckhand'))

    def override_config(self, name, override, group=None):
        CONF.set_override(name, override, group)
        self.addCleanup(CONF.clear_override, name, group)


class DeckhandWithDBTestCase(DeckhandTestCase):

    def setUp(self):
        super(DeckhandWithDBTestCase, self).setUp()
        self.override_config('connection', "sqlite://", group='database')
<<<<<<< 277c22816748669916dd7256f9260503955ee773
        db_api.setup_db()
        self.addCleanup(db_api.drop_db)
=======
        # db_api.setup_db()
        # self.addCleanup(db_api.drop_db)
>>>>>>> Add layering policy pre-validation schema
