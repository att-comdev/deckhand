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

import abc
import copy

from oslo_log import log as logging

from deckhand.tests import test_utils

LOG = logging.getLogger(__name__)


class DeckhandFactory(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def gen(self, *args):
        pass

    @abc.abstractmethod
    def gen_test(self, *args, **kwargs):
        pass


class DocumentSecretFactory(DeckhandFactory):
    """Class for auto-generating document secrets templates for testing.

    Returns formats that adhere to the following supported schemas:

      * deckhand/Certificate/v1
      * deckhand/CertificateKey/v1
      * deckhand/Passphrase/v1
    """

    DOCUMENT_SECRET_TEMPLATE = {
        "data": {
        },
        "metadata": {
            "schema": "metadata/Document/v1",
            "name": "application-api",
            "storagePolicy": ""
        },
        "schema": "deckhand/%s/v1"
    }

    def __init__(self):
        """Constructor for ``DocumentSecretFactory``.

        Returns a template whose YAML representation is of the form::

            ---
            schema: deckhand/Certificate/v1
            metadata:
              schema: metadata/Document/v1
              name: application-api
              storagePolicy: cleartext
            data: |-
              -----BEGIN CERTIFICATE-----
              MIIDYDCCAkigAwIBAgIUKG41PW4VtiphzASAMY4/3hL8OtAwDQYJKoZIhvcNAQEL
              ...snip...
              P3WT9CfFARnsw2nKjnglQcwKkKLYip0WY2wh3FE7nrQZP6xKNaSRlh6p2pCGwwwH
              HkvVwA==
              -----END CERTIFICATE-----
            ...
        """
        pass

    def gen(self, schema, storage_policy):
        # TODO: Check whether schema is one of the supported types, or else
        # raise a ValueError.

        document_secret_template = copy.deepcopy(self.DOCUMENT_SECRET_TEMPLATE)

        document_secret_template['metadata']['storagePolicy'] = storage_policy
        document_secret_template['schema'] = (
            document_secret_template['schema'] % schema)

        return document_secret_template

    def gen_test(self):
        pass
