Document Validation
===================

Overview
--------

The validation system provides a unified approach to complex validations that
require coordination of multiple documents and business logic that resides in
consumer services.

Services can report success or failure of named validations for a given
revision. Those validations can then be referenced by many `ValidationPolicy`
control documents. The intended purpose use is to allow a simple mapping that
enables consuming services to be able to quickly check whether the
configuration in Deckhand is in a valid state for performing a specific
action.

Deckhand-Provided Validations
-----------------------------

In addition to allowing 3rd party services to report configurable validation
statuses, Deckhand provides a few internal validations which are made
available immediately upon document ingestion.

Here is a list of internal validations:

* ``deckhand-schema-validation`` - All concrete documents in the
  revision successfully pass their JSON schema validations. Will cause
  this to report an error.
* ``deckhand-policy-validation`` - All required policy documents are in-place,
  and existing documents conform to those policies.  E.g. if a 3rd party
  document specifies a `layer` that is not present in the layering policy,
  that will cause this validation to report an error.


Externally Provided Validations
-------------------------------

Control documents (documents which have
``metadata.schema=metadata/Control/v1``),
are special and are used to control the behavior of Deckhand at runtime. Only
the following types of control documents are allowed.

DataSchema
^^^^^^^^^^

`DataSchema` documents are used by various services to register new schemas
that Deckhand can use for validation. No `DataSchema` documents with names
beginning with `deckhand/` or `metadata/` are allowed.  Tme `metadata.name`
field of each `DataSchema` document specifies the top level `schema` that it
is used to validate.

The contents of its `data` key are expected to be the json schema definition
for the target document type from the target's top level `data` key down.

.. code-block:: yaml

    ---
    schema: deckhand/DataSchema/v1  # This specifies the official JSON schema meta-schema.
    metadata:
      schema: metadata/Control/v1
      name: promenade/Node/v1  # Specifies the documents to be used for validation.
      labels:
        application: promenade
    data:  # Valid JSON Schema is expected here.
      $schema: http://blah
    ...

Validation Module
-----------------

.. autoclass:: deckhand.engine.document_validation.DocumentValidation
   :members:
   :private-members:
