..
  Copyright 2018 AT&T Intellectual Property.
  All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _encryption:

Data Encryption
===============

Deckhand uses `Barbican`_ to encrypt sensitive document data. Encryption
entails encrypting the entire ``data`` section of a document by
setting its ``metadata.storagePolicy`` to ``encrypted``.

.. note::

  Note that encryption of document data incurs **runtime overhead** as the
  price of encryption is performance. As a general rule, the more documents
  with ``storagePolicy: encrypted``, the longer it will take to render the
  documents, particularly because Barbican has a built-in `restriction`_
  around retrieving only one encrypted payload a time. This means that
  if 50 documents have ``storagePolicy: encrypted`` within a revision, then
  Deckhand must perform 50 API calls to Barbican when rendering the documents
  for that revision.

Encrypted documents, like cleartext documents, are stored in Deckhand's
database, except that the ``data`` section of each encrypted document
has a reference to the actual Barbican secret payload. The reference
is innocuous and is safe to store inside Deckhand.

.. _Barbican: https://docs.openstack.org/barbican/latest/api/
.. _restriction: https://docs.openstack.org/barbican/latest/api/reference/secrets.html#get-v1-secrets

Supported Data Types
--------------------

Barbican supports encrypting `any`_ data type via its "opaque" secret type.
Thus, Deckhand supports encryption of any data type by exploiting this
secret type.

However, Deckhand will attempt to use Barbican's `other`_ secret types where
possible. For example, Deckhand will use "public" for document types with kind
``PublicKey``.

.. _any: https://github.com/openstack/barbican/blob/7991f8b4850d76d97c3482428638f788f5798a56/barbican/plugin/interface/secret_store.py#L272
.. _other: https://docs.openstack.org/barbican/latest/api/reference/secret_types.html
