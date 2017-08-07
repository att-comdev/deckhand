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


class TestRevisionTagsApi(test_base.TestFunctionalBase):

    def setUp(self):
        super(TestRevisionTagsApi, self).setUp()
        self.revision_id = self._create_revision()

    def _create_revision(self):
        yaml_data = self._read_test_resource('sample_document')
        resp = self.app.simulate_post('/api/v1.0/documents', body=yaml_data)
        resp_json = [d for d in yaml.safe_load_all(resp.text)][0]
        return resp_json['revision_id']

    def _create_revision_tag(self, with_data=False):
        rand_prefix = test_utils.rand_name(self.__class__.__name__)
        rand_tag = rand_prefix + '-Tag'
        rand_data = {rand_prefix + '-Key': rand_prefix + '-Val'}

        if with_data:
            resp = self.app.simulate_post(
                '/api/v1.0/revisions/%s/tags/%s'
                % (self.revision_id, rand_tag), body=json.dumps(rand_data))
        else:
            resp = self.app.simulate_post(
                '/api/v1.0/revisions/%s/tags/%s'
                % (self.revision_id, rand_tag))

        return resp, rand_tag, rand_data

    def _verify_deleted(self, tag):
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/tags/%s' % (self.revision_id, tag))
        self.assertEqual(falcon.HTTP_404, resp.status)

        content = json.loads(resp.content)
        error_re = ('The requested tag .* for revision .* was not found.')
        self.assertIn('message', content)
        self.assertRegexpMatches(content['message'], error_re)

    def test_create_revision_tag_no_data(self):
        resp, rand_tag, _ = self._create_revision_tag()
        self.assertEqual(falcon.HTTP_201, resp.status)

        revision_tags = [t for t in yaml.safe_load_all(resp.text)]
        self.assertEqual(1, len(revision_tags))
        self.assertIsNone(revision_tags[0]['data'])
        self.assertEqual(rand_tag, revision_tags[0]['tag'])

    def test_create_revision_tag_with_data(self):
        resp, rand_tag, rand_data = self._create_revision_tag(with_data=True)
        self.assertEqual(falcon.HTTP_201, resp.status)

        revision_tags = [t for t in yaml.safe_load_all(resp.text)]
        self.assertEqual(1, len(revision_tags))
        self.assertEqual(rand_data, revision_tags[0]['data'])
        self.assertEqual(rand_tag, revision_tags[0]['tag'])

    def test_show_revision_tag(self):
        _, rand_tag, _ = self._create_revision_tag()
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/tags/%s' % (self.revision_id, rand_tag))
        self.assertEqual(falcon.HTTP_200, resp.status)

        resp_tag = yaml.safe_load(resp.text)
        self.assertIn('tag', resp_tag)
        self.assertIn('data', resp_tag)
        self.assertEqual(rand_tag, resp_tag['tag'])
        self.assertEmpty(resp_tag['data'])

    def test_list_revision_tags(self):
        expected_tags = [self._create_revision_tag()[1] for _ in range(3)]
        resp = self.app.simulate_get(
            '/api/v1.0/revisions/%s/tags' % self.revision_id)
        self.assertEqual(falcon.HTTP_200, resp.status)

        resp_tags = [t for t in yaml.safe_load_all(resp.text)]
        self.assertEqual(3, len(resp_tags))

        for idx, resp_tag in enumerate(resp_tags):
            self.assertIn('tag', resp_tag)
            self.assertIn('data', resp_tag)
            self.assertEqual(expected_tags[idx], resp_tag['tag'])
            self.assertEmpty(resp_tag['data'])

    def test_delete_revision_tag(self):
        _, tag, _ = self._create_revision_tag()
        resp = self.app.simulate_delete(
            '/api/v1.0/revisions/%s/tags/%s' % (self.revision_id, tag))
        self.assertEqual(falcon.HTTP_204, resp.status)
        self.assertEmpty(resp.text)
        self._verify_deleted(tag)

    def test_delete_all_revision_tags(self):
        expected_tags = [self._create_revision_tag()[1] for _ in range(3)]
        resp = self.app.simulate_delete(
            '/api/v1.0/revisions/%s/tags' % self.revision_id)
        self.assertEqual(falcon.HTTP_204, resp.status)
        self.assertEmpty(resp.text)
        for tag in expected_tags:
            self._verify_deleted(tag)
