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

from oslo_log import log as logging

from deckhand.db.sqlalchemy import api as db_api
from deckhand.engine import document as document_wrapper
from deckhand import utils

LOG = logging.getLogger(__name__)


class SecretSubstitution(object):
    """Class for document substitution logic for YAML files."""

    def __init__(self, documents):
        """SecretSubstitution constructor.

        :param documents: List of YAML documents in dictionary format that are
            candidates for secret substitution. This class will automatically
            detect documents that require substitution; documents need not be
            filtered prior to being passed to the constructor.
        """
        if not isinstance(documents, (list, tuple)):
            documents = [documents]
        substitute_docs = []
        for doc in documents:
            document = document_wrapper.Document(doc)
            if document.get_substitutions():
                substitute_docs.append(document)
        self.documents = substitute_docs

    def substitute_all(self):
        LOG.debug('Substituting secrets for documents: %s', self.documents)
        substituted_docs = []

        for doc in self.documents:
            for sub in doc.get_substitutions():
                src_schema = sub['src']['schema']
                src_name = sub['src']['name']
                src_path = sub['src']['path']
                if src_path == '.':
                    src_path = 'secret'

                # TODO(fmontei): Use secrets_manager for this logic. Need to
                # check Barbican for the secret if it has been encrypted.
                src_doc = db_api.document_get(schema=src_schema, name=src_name)
                src_secret = utils.jsonpath_parse(src_doc['data'], src_path)

                dest_path = sub['dest']['path']
                dest_pattern = sub['dest'].get('pattern', None)
                substituted_data = utils.jsonpath_replace(
                    doc['data'], src_secret, dest_path, dest_pattern)
                doc['data'].update(substituted_data)

            substituted_docs.append(doc.to_dict())
        return substituted_docs
