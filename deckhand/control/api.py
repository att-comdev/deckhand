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
import sys

import falcon
from oslo_config import cfg
from oslo_log import log as logging
from oslo_policy import policy as policy

from deckhand.control import base
from deckhand.control import buckets
from deckhand.control import revision_diffing
from deckhand.control import revision_documents
from deckhand.control import revision_tags
from deckhand.control import revisions
from deckhand.control import rollback
from deckhand.control import versions
from deckhand.db.sqlalchemy import api as db_api
from deckhand import policies
from deckhand import policy as deckhand_policy

CONF = cfg.CONF
logging.register_options(CONF)

# TODO(fmontei): Include deckhand-paste.ini later.
CONFIG_FILES = ['deckhand.conf']


def _get_config_files(env=None):
    if env is None:
        env = os.environ
    dirname = env.get('OS_DECKHAND_CONFIG_DIR', '/etc/deckhand').strip()
    return [os.path.join(dirname, config_file) for config_file in CONFIG_FILES]


def start_api():
    """Main entry point for initializing the Deckhand API service.

    Create routes for the v1.0 API and sets up logging.
    """
    config_files = _get_config_files()
    CONF([], project='deckhand', default_config_files=config_files)
    logging.setup(CONF, "deckhand")

    LOG = logging.getLogger(__name__)
    LOG.info('Initiated Deckhand logging.')

    if '--no-policy' in sys.argv:
        # WARNING(fmontei): Including this pyargv to uwsgi will run Deckhand
        # without policy enforcement. This should only be done for functional
        # testing.
        # TODO(fmontei): Remove this once Keystone has been integrated into
        # functional testing script.
        deckhand_policy._ENFORCER = policy.Enforcer(CONF)
        deckhand_policy.register_rules(
            deckhand_policy._ENFORCER,
            [policy.RuleDefault(r.name, '') for r in policies.list_rules()])
        LOG.warning('Running Deckhand without policy enforcement. '
                    'This should only be done for functional testing.')

    db_api.drop_db()
    db_api.setup_db()

    control_api = falcon.API(request_type=base.DeckhandRequest)

    v1_0_routes = [
        ('bucket/{bucket_name}/documents', buckets.BucketsResource()),
        ('revisions', revisions.RevisionsResource()),
        ('revisions/{revision_id}', revisions.RevisionsResource()),
        ('revisions/{revision_id}/diff/{comparison_revision_id}',
            revision_diffing.RevisionDiffingResource()),
        ('revisions/{revision_id}/documents',
            revision_documents.RevisionDocumentsResource()),
        ('revisions/{revision_id}/tags', revision_tags.RevisionTagsResource()),
        ('revisions/{revision_id}/tags/{tag}',
            revision_tags.RevisionTagsResource()),
        ('rollback/{revision_id}', rollback.RollbackResource())
    ]

    for path, res in v1_0_routes:
        control_api.add_route(os.path.join('/api/v1.0', path), res)

    control_api.add_route('/versions', versions.VersionsResource())

    return control_api


if __name__ == '__main__':
    start_api()
