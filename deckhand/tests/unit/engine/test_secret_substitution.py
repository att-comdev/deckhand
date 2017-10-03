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

from deckhand.engine import layering
from deckhand.engine import substitution
from deckhand import errors
from deckhand import factories
from deckhand.tests import test_utils
from deckhand.tests.unit.db import base as test_base


class TestDocumentLayering(test_base.TestDbBase):

    def test_secret_substitution(self):
        self.document_factory = factories.DocumentFactory(1, [1])
        self.secrets_factory = factories.DocumentSecretFactory()
        certificate = self.secrets_factory.gen_test(
            'Certificate', 'cleartext', data={'secret': 'CERTIFICATE DATA'})
        certificate['metadata']['name'] = 'example-cert'

        document_mapping = {
            "_GLOBAL_SUBSTITUTIONS_1_": [{
                "dest": {
                    "path": ".chart.values.tls.certificate"
                },
                "src": {
                    "schema": "deckhand/Certificate/v1",
                    "name": "example-cert",
                    "path": "."
                }

            }]
        }
        documents = self.document_factory.gen_test(document_mapping,
                                                   global_abstract=False)
        documents[-1]['schema'] = 'armada/Chart/v1'

        bucket_name = test_utils.rand_name('bucket')
        documents = self.create_documents(
            bucket_name, [certificate] + [documents[-1]])

        from pprint import pprint
        pprint(documents)

        secret_substitution = substitution.SecretSubstitution(documents)
        secret_substitution.substitute_all()
