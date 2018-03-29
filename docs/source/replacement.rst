..
  Copyright 20178 AT&T Intellectual Property.
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

.. _replacement:

Document Replacement
====================

.. note::

  Document replacement is an advanced concept in Deckhand. This section assumes
  that the reader already has an understand of :ref:`layering` and
  :ref:`substitution`. 

What is Replacement?
--------------------

Replacement allows particular values in a parent document to be overidden,
while still allowing the parent document to be used as a substitution or
layering source for other documents.

Why Replacement?
----------------

Layering without Replacement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

  In the examples that follow the ``data`` section of the documents can be
  arbitrarily large.

Layering without replacement can introduce a lot of data duplication across
documents. Take the following use case: Some sites need to be deployed with
log debugging *enabled* and other sites need to be deployed with log debugging
*disabled*.

To achieve this, two top-layer documents can be created:

::

  ---
  schema: armada/Chart/v1
  metadata:
    name: ucp-deckhand-1
    layeringDefinition:
      layer: global
      ...
  data:
    debug: false
    ...

And:

::

  ---
  schema: armada/Chart/v1
  metadata:
    name: ucp-deckhand-2
    layeringDefinition:
      layer: global
      ...
  data:
    debug: true
    ...

However, what if the only thing that differs between the two documents is just
``debug: true|false`` and every other value in both documents is precisely the
same?

Clearly, the pattern above leads to a lot of data duplication.

Layering with Replacement
^^^^^^^^^^^^^^^^^^^^^^^^^

Using document replacement, the above duplication can be partially eliminated.
For example:

::

  ---
  schema: armada/Chart/v1
  metadata:
    name: ucp-deckhand
    labels:
      selector: foo
    layeringDefinition:
      layer: global
      ...
  data:
    debug: false
    ...

And:

::

  ---
  schema: armada/Chart/v1
  metadata:
    # Note the child document has the same `metadata.name` and `schema` as its
    # parent.
    name: ucp-deckhand
    replacement: true
    parentSelector:
      selector: foo
    layeringDefinition:
      layer: site
      actions:
        - method: merge
          path: .
        - method: replace
          path: .debug
          value: true
  data: {}

In the case above, for sites that require ``debug: false``, the only the
global-level document should be included in the payload to Deckhand, along
with all other documents required for site deployment.

However, for sites that require ``debug: true``, both documents should be
included in the payload to Deckhand, along with all other documents required
for site deployment.

Implications for Pegleg
^^^^^^^^^^^^^^^^^^^^^^^

In practice, when using `Pegleg`_, each document above can be placed in a
separate file and Pegleg can either reference *only* the parent document
if log debugging needs to be enabled or *both* documents if log debugging
needs to be disabled. This pattern allows data duplication to be lessened.

.. _Pegleg: http://pegleg.readthedocs.io/en/latest/
