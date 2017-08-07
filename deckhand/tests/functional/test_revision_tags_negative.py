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

import yaml

import falcon
from oslo_serialization import jsonutils as json

from deckhand.tests.functional import base as test_base
from deckhand.tests import test_utils


class TestRevisionTagsApiNegative(test_base.TestFunctionalBase):

    def setUp(cls):
        super(TestRevisionTagsApiNegative, cls).setUp()
        cls.revision_id = cls._create_revision()

    def _create_revision(cls):
        # TODO(fmontei): All such method will be moved to a client in a
        # separate file for common consumption.
        yaml_data = cls._read_test_resource('sample_document')
        resp = cls.app.simulate_post('/api/v1.0/documents', body=yaml_data)
        resp_dict = [d for d in yaml.safe_load_all(resp.text)][0]
        return resp_dict['revision_id']

    def test_create_revision_tag_with_invalid_data(self):
        rand_prefix = test_utils.rand_name(self.__class__.__name__)
        rand_tag = rand_prefix + '-Tag'
        error_re = ('The requested tag data .* must either be null or '
                    'dictionary.')

        resp = self.app.simulate_post(
            '/api/v1.0/revisions/%s/tags/%s' % (self.revision_id, rand_tag),
            body=json.dumps(rand_prefix))
        self.assertEqual(falcon.HTTP_400, resp.status)
        self.assertEmpty(resp.text)

        content = json.loads(resp.content)
        self.assertIn('message', content)
        self.assertRegexpMatches(content['message'], error_re)
