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

import collections

from deckhand.common import utils
from deckhand.control import common
from deckhand.control.views import validation
from deckhand import types


class ViewBuilder(common.ViewBuilder):
    """Model revision API responses as a python dictionary."""

    _collection_name = 'revisions/%s'

    @classmethod
    def list(cls, revisions):
        resp_body = {
            'count': len(revisions),
            'results': []
        }

        for revision in revisions:
            body = {'tags': set(), 'buckets': set()}
            rev_documents = revision.pop('documents')

            for attr in ('id', 'created_at'):
                body[utils.to_camel_case(attr)] = revision[attr]
                body['url'] = cls._gen_url(revision, 'id')

            body['tags'].update([t['tag'] for t in revision['tags']])
            body['buckets'].update(
                [d['bucket_name'] for d in rev_documents])

            body['tags'] = sorted(body['tags'])
            body['buckets'] = sorted(body['buckets'])

            resp_body['results'].append(body)

        return resp_body

    @classmethod
    def show(cls, revision):
        """Generate view for showing revision details.

        Each revision's documents should only be validation policies.
        """
        validation_policies = []
        tags = collections.OrderedDict()
        success_status = 'success'

        for vp in [d for d in revision['documents']
                   if d['schema'].startswith(types.VALIDATION_POLICY_SCHEMA)]:
            # TODO(fmontei): All this needs to be reworked in light of the fact
            # that ValidationPolicy concept will likely be reworked or
            # deprecated.
            validation_policy = {}
            validation_policy['name'] = vp.get('name')
            validation_policy['url'] = validation.ViewBuilder._gen_url(
                vp, 'id')
            try:
                validations = vp['data']['validations']
                validation_policy['status'] = 'failure' if 'failure' in [
                    v['status'] for v in validations
                ] else 'success'
            except KeyError:
                validation_policy['status'] = 'unknown'

            validation_policies.append(validation_policy)

            if validation_policy['status'] != 'success':
                success_status = 'failed'

        for tag in revision['tags']:
            tags.setdefault(tag['tag'], tag['data'])

        buckets = sorted(
            set([d['bucket_name'] for d in revision['documents']]))

        return {
            'id': revision.get('id'),
            'createdAt': revision.get('created_at'),
            'url': cls._gen_url(revision, 'id'),
            'validationPolicies': validation_policies,
            'status': success_status,
            'tags': dict(tags),
            'buckets': buckets
        }
