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

from deckhand.control import common


class ViewBuilder(common.ViewBuilder):
    """Model revision API responses as a python dictionary."""

    _collection_name = 'revisions'

    def list(self, revisions):
        resp_body = {
            'count': len(revisions),
            'results': [],
            'tags': set(),
            'buckets': set()
        }

        for revision in revisions:
            body = {}
            rev_documents = revision.pop('documents')

            for attr in ('id', 'created_at'):
                body[common.to_camel_case(attr)] = revision[attr]
            resp_body['results'].append(body)

            resp_body['tags'].update([t['tag'] for t in revision['tags']])
            resp_body['buckets'].update(
                [d['bucket_id'] for d in rev_documents])

        # Sort the collections to facilitate functional testing.
        resp_body['tags'] = sorted(resp_body['tags'])
        resp_body['buckets'] = sorted(resp_body['buckets'])

        return resp_body

    def show(self, revision):
        """Generate view for showing revision details.

        Each revision's documents should only be validation policies.
        """
        validation_policies = []
        tags = {}
        success_status = 'success'

        for vp in revision['validation_policies']:
            validation_policy = {}
            validation_policy['name'] = vp.get('name')
            validation_policy['url'] = self._gen_url(vp)
            try:
                validation_policy['status'] = vp['data']['validations'][0][
                    'status']
            except KeyError:
                validation_policy['status'] = 'unknown'

            validation_policies.append(validation_policy)

            if validation_policy['status'] != 'success':
                success_status = 'failed'

        # TODO(fmontei): For the time being we're only returning the tag name,
        # but eventually we'll return data associated with the data, which is
        # why this is a dictionary, not a list.
        for tag in revision['tags']:
            tags.setdefault(tag['tag'], {'name': tag['tag']})

        buckets = sorted(set([d['bucket_id'] for d in revision['documents']]))

        return {
            'id': revision.get('id'),
            'createdAt': revision.get('created_at'),
            'url': self._gen_url(revision),
            'validationPolicies': validation_policies,
            'status': success_status,
            'tags': tags,
            'buckets': buckets
        }
