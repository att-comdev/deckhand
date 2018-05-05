..
  Copyright 2017 AT&T Intellectual Property.
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

.. _substitution:

Document Substitution
=====================

Document substitution, simply put, allows one document to overwrite *parts* of
its own data with that of another document. Substitution involves a source
document sharing data with a destination document, which replaces its own data
with the shared data.

Substitution is primarily designed as a mechanism for inserting secrets into
configuration documents, but works for unencrypted source documents as well.
Substitution is applied at each layer after all merge actions occur.

Substitution works like this:

The ``src`` document is resolved via the ``src.schema`` and ``src.name``
keys and the ``src.path`` key is used relative to the source document's
``data`` section to retrieve the substitution data, which is then injected
into the ``data`` section of the destination document using the ``dest.path``
key. The ``dest.pattern`` is optional and has the following constraints:

* ``dest.path`` must already exist in the ``data`` section of the destination
  document.
* The ``dest.path`` value **must** be a string.
* The ``dest.pattern`` must be a regular expression string.
* The ``dest.pattern`` must be found in the value of ``dest.path``.

If all the constraints above are correct, then the substitution source data
is injected into the destination document's ``data`` section, keyed
with the ``dest.path`` value, precisely where the ``dest.pattern``
value indicates inside the ``dest.path`` value.

.. note::

  Substitution is only applied to the ``data`` section of a document. This is
  because a document's ``metadata`` and ``schema`` sections should be
  immutable within the scope of a revision, for obvious reasons.

Rendering Documents with Substitution
-------------------------------------

Concrete (non-abstract) documents can be used as a source of substitution
into other documents. This substitution is layer-independent, so given the 3
layer example above, which includes ``global``, ``region`` and ``site`` layers,
a document in the ``region`` layer could insert data from a document in the
``site`` layer.

Example
^^^^^^^

Here is a sample set of documents demonstrating substitution:

.. code-block:: yaml

  ---
  schema: deckhand/Certificate/v1
  metadata:
    name: example-cert
    storagePolicy: cleartext
    layeringDefinition:
      layer: site
  data: |
    CERTIFICATE DATA
  ---
  schema: deckhand/CertificateKey/v1
  metadata:
    name: example-key
    storagePolicy: encrypted
    layeringDefinition:
      layer: site
  data: |
    KEY DATA
  ---
  schema: deckhand/Passphrase/v1
  metadata:
    name: example-password
    storagePolicy: encrypted
    layeringDefinition:
      layer: site
  data: my-secret-password
  ---
  schema: armada/Chart/v1
  metadata:
    name: example-chart-01
    storagePolicy: cleartext
    layeringDefinition:
      layer: region
    substitutions:
      - dest:
          path: .chart.values.tls.certificate
        src:
          schema: deckhand/Certificate/v1
          name: example-cert
          path: .
      - dest:
          path: .chart.values.tls.key
        src:
          schema: deckhand/CertificateKey/v1
          name: example-key
          path: .
      - dest:
          path: .chart.values.some_url
          pattern: INSERT_[A-Z]+_HERE
        src:
          schema: deckhand/Passphrase/v1
          name: example-password
          path: .
  data:
    chart:
      details:
        data: here
      values:
        some_url: http://admin:INSERT_PASSWORD_HERE@service-name:8080/v1
  ...

The rendered document will look like:

.. code-block:: yaml

  ---
  schema: armada/Chart/v1
  metadata:
    name: example-chart-01
    storagePolicy: cleartext
    layeringDefinition:
      layer: region
    substitutions:
      - dest:
          path: .chart.values.tls.certificate
        src:
          schema: deckhand/Certificate/v1
          name: example-cert
          path: .
      - dest:
          path: .chart.values.tls.key
        src:
          schema: deckhand/CertificateKey/v1
          name: example-key
          path: .
      - dest:
          path: .chart.values.some_url
          pattern: INSERT_[A-Z]+_HERE
        src:
          schema: deckhand/Passphrase/v1
          name: example-password
          path: .
  data:
    chart:
      details:
        data: here
      values:
        some_url: http://admin:my-secret-password@service-name:8080/v1
        tls:
          certificate: |
            CERTIFICATE DATA
          key: |
            KEY DATA
  ...

This substitution is also ``schema`` agnostic, meaning that source and
destination documents can have a different ``schema``.

Substitution of Encrypted Data
------------------------------

Deckhand allows :ref:`data to be encrypted using Barbican <encryption>`.
Substitution of encrypted data works the same as substitution of cleartext
data.
