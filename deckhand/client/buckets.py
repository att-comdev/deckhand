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

class Controller(object):
    def __init__(self, http_client):
        self.http_client = http_client

    def update(self, bucket_name, documents):
        """Create, update or delete documents from a bucket.

        :param bucket_name: The name of the bucket.
        :type bucket_name: str
        :param documents: YAML-formatted documents.
        :type documents: str
        """
        url = '/api/v1.0/buckets/%s/documents' % bucket_name
        return self.http_client.put(url, data=documents)
