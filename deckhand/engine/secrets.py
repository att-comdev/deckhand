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

from deckhand.barbican import driver


class SecretsResource(object):
    """Internal API resource for interacting with Barbican.

    Currently only supports Barbican.
    """

    def __init__(self, **kwargs):
        self.barbican_driver = driver.BarbicanDriver()

    def post(self, document):
        """Store document secrets securely.

        Ordinarily, Deckhand documents are stored directly in Deckhand's
        database. However, secret data (contained in the data section for the
        documents with the schemas above) must be stored using a secure storage
        service like Barbican.

        Documents with metadata.storagePolicy == "clearText" have their secrets
        stored directly in Deckhand/

        Documents with metadata.storagePolicy == "encrypted" are stored in
        Barbican directly. Deckhand in turn stores the reference returned
        by Barbican in the ``Document`` model that represents that YAML
        document that originally contained the secret.

        :param document: A Deckhand document with one of the following schemas:

            * deckhand/Certificate/v1
            * deckhand/CertificateKey/v1
            * deckhand/Passphrase/v1
        """
        encryption_type = document['metadata']['storagePolicy']
        secret_type = self._get_secret_type(document['schema'])

        kwargs = {'name': secret_name, 'secret_type': secret_type}
        resp = self.barbican_driver.create_secret(**kwargs)
        secret_ref = resp['secret_ref']

        # Store secret_ref in database for document.

    def _get_secret_type(self, schema):
        """Get the Barbican secret type based on the following mapping:

        deckhand/Certificate/v1 => certificate
        deckhand/CertificateKey/v1 => private 
        deckhand/Passphrase/v1 => passphrase

        :param schema: The document's schema.
        :returns: The value corresponding to the mapping above.
        """
        return schema.split('/')[1].lower().strip()
