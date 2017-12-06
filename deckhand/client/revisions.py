# Copyright 2017 AT&T Intellectual Property.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from deckhand.client import base


class Revision(base.Resource):
    def __repr__(self):
        try:
            return ("<Revision ID: %s>" % self.id)
        except:
            return ("<Revision Diff>")

class RevisionManager(base.Manager):
    """Manage :class:`Bucket` resources."""
    resource_class = Revision

    def list(self, **filters):
        """Get a list of revisions."""
        url = '/api/v1.0/revisions'
        return self._list(url, filters=filters)   

    def get(self, revision_id):
        """Get details for a revision."""
        url = '/api/v1.0/revisions/%s' % revision_id
        return self._get(url)      

    def diff(self, revision_id, comparison_revision_id):
        """Get revision diff between two revisions."""
        url = '/api/v1.0/revisions/%s/diff/%s' % (
            revision_id, comparison_revision_id)
        return self._get(url)
