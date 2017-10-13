## Buckets

Collections of documents, called buckets, are managed together.  All documents
belong to a bucket and all documents that are part of a bucket must be fully
specified together.

To create or update a new document in, e.g. bucket `mop`, one must PUT the
entire set of documents already in `mop` along with the new or modified
document.  Any documents not included in that PUT will be automatically
deleted in the created revision.

This feature allows the separation of concerns when delivering different
categories of documents, while making the delivered payload more declarative.

## Revision History

Documents will be ingested in batches which will be given a revision index.
This provides a common language for describing complex validations on sets of
documents.

Revisions can be thought of as commits in a linear git history, thus looking
at a revision includes all content from previous revisions.

## Validation

The validation system provides a unified approach to complex validations that
require coordination of multiple documents and business logic that resides in
consumer services.

Services can report success or failure of named validations for a given
revision. Those validations can then be referenced by many `ValidationPolicy`
control documents. The intended purpose use is to allow a simple mapping that
enables consuming services to be able to quickly check whether the
configuration in Deckhand is in a valid state for performing a specific
action.

### Deckhand-Provided Validations

In addition to allowing 3rd party services to report configurable validation
statuses, Deckhand provides a few internal validations which are made
available immediately upon document ingestion.

Here is a list of internal validations:

* `deckhand-document-schema-validation` - All concrete documents in the
  revision successfully pass their JSON schema validations. Will cause
  this to report an error.
* `deckhand-policy-validation` - All required policy documents are in-place,
  and existing documents conform to those policies.  E.g. if a 3rd party
  document specifies a `layer` that is not present in the layering policy,
  that will cause this validation to report an error.

## Access Control

Deckhand will use standard OpenStack Role Based Access Control using the
following actions:

- `deckhand:list_cleartext_documents` - Read unencrypted documents.
- `deckhand:list_encrypted_documents` - Read (including substitution and layering)
  encrypted documents.
- `deckhand:list_validations` - Read validation policy status, and validation results,
- `deckhand:create_validation` - Write validation results.
  including error messages.
- `deckhand:create_cleartext_documents` - Create, update or delete unencrypted documents.
- `deckhand:create_encrypted_documents` - Create, update or delete encrypted documents.
- `deckhand:show_revision` - Show revision details.
- `deckhand:list_revisions` - List all revisions.
- `deckhand:delete_revisions` - Delete all revisions. Equivalent to effectively
  purging all data from the database.
- `deckhand:show_revision_diff` - Show revision diff for two revisions.
- `deckhand:create_tag` - Create a revision tag.
- `deckhand:show_tag` - Show revision tag details.
- `deckhand:list_tags` - List all revision tags.
- `deckhand:delete_tag` - Delete a revision tag.
- `deckhand:delete_tags` - Delete all revision tags.

## API

This API will only support YAML as a serialization format. Since the IETF
does not provide an official media type for YAML, this API will use
`application/x-yaml`.

This is a description of the `v1.0` API. Documented paths are considered
relative to `/api/v1.0`.

### PUT `/bucket/{bucket_name}/documents`

Accepts a multi-document YAML body and creates a new revision that updates the
contents of the `bucket_name` bucket.  Documents from the specified bucket that
exist in previous revisions, but are absent from the request are removed from
that revision (though still accessible via older revisions).

Documents in other buckets are not changed and will be included in queries for
documents of the newly created revision.

Updates are detected based on exact match to an existing document of `schema` +
`metadata.name`.  It is an error that responds with `409 Conflict` to attempt
to PUT a document with the same `schema` + `metadata.name` as an existing
document from a different bucket in the most-recent revision.

This endpoint is the only way to add, update, and delete documents. This
triggers Deckhand's internal schema validations for all documents.

If no changes are detected, a new revision should not be created. This allows
services to periodically re-register their schemas without creating
unnecessary revisions.

This endpoint uses the `deckhand:list_cleartext_documents` and
`deckhand:list_encrypted_documents` actions.

### GET `/revisions/{revision_id}/documents`

Returns a multi-document YAML response containing all the documents matching
the filters specified via query string parameters. Returned documents will be
as originally added with no substitutions or layering applied.

Supported query string parameters:

* `schema` - string, optional - The top-level `schema` field to select. This
  may be partially specified by section, e.g., `schema=promenade` would select all
  `kind` and `version` schemas owned by promenade, or `schema=promenade/Node`
  which would select all versions of `promenade/Node` documents. One may not
  partially specify the namespace or kind, so `schema=promenade/No` would not
  select `promenade/Node/v1` documents, and `schema=prom` would not select
  `promenade` documents.
* `metadata.name` - string, optional
* `metadata.layeringDefinition.abstract` - string, optional - Valid values are
  the "true" and "false".
* `metadata.layeringDefinition.layer` - string, optional - Only return documents from
  the specified layer.
* `metadata.label` - string, optional, repeatable - Uses the format
  `metadata.label=key=value`. Repeating this parameter indicates all
  requested labels must apply (AND not OR).
* `sort` - string, optional, repeatable - Defines the sort order for returning
  results.  Default is by creation date.  Repeating this parameter indicates use
  of multi-column sort with the most significant sorting column applied first.
* `status.bucket` - string, optional, repeatable - Used to select documents
  only from a particular bucket.  Repeating this parameter indicates documents
  from any of the specified buckets should be returned.

This endpoint uses the `deckhand:list_cleartext_documents` and
`deckhand:list_encrypted_documents` actions.

### GET `/revisions/{revision_id}/rendered-documents`

Returns a multi-document YAML of fully layered and substituted documents. No
abstract documents will be returned. This is the primary endpoint that
consumers will interact with for their configuration.

Valid query parameters are the same as for
`/revisions/{revision_id}/documents`, minus the paremters in
`metadata.layeringDetinition`, which are not supported.

This endpoint uses the `deckhand:list_cleartext_documents` and
`deckhand:list_encrypted_documents` actions.

### GET `/revisions`

Lists existing revisions and reports basic details including a summary of
validation status for each `deckhand/ValidationPolicy` that is part of that
revision.

Supported query string parameters:

* `tag` - string, optional, repeatable - Used to select revisions that have
  been tagged with particular tags.

Sample response:

```yaml
---
count: 7
next: https://deckhand/api/v1.0/revisions?limit=2&offset=2
prev: null
results:
  - id: 1
    url: https://deckhand/api/v1.0/revisions/1
    createdAt: 2017-07-14T21:23Z
    buckets: [mop]
    tags: [a, b, c]
    validationPolicies:
      site-deploy-validation:
        status: failure
  - id: 2
    url: https://deckhand/api/v1.0/revisions/2
    createdAt: 2017-07-16T01:15Z
    buckets: [flop, mop]
    tags: [b]
    validationPolicies:
      site-deploy-validation:
        status: success
...
```

This endpoint uses the `deckhand:show_revision` action.

### DELETE `/revisions`

Permanently delete all documents.  This removes all revisions and resets the
data store.

This endpoint uses the `deckhand:delete_revisions` action.

### GET `/revisions/{{revision_id}}`

Get a detailed description of a particular revision. The status of each
`ValidationPolicy` belonging to the revision is also included. Valid values
for the status of each validation policy are:

* `success` - All validations associated with the policy are `success`.
* `failure` - Any validation associated with the policy has status `failure`,
  `expired` or `missing`.

Sample response:

```yaml
---
id: 1
url: https://deckhand/api/v1.0/revisions/1
createdAt: 2017-07-14T021:23Z
buckets: [mop]
tags:
  a:
    name: a
    url: https://deckhand/api/v1.0/revisions/1/tags/a
validationPolicies:
  site-deploy-validation:
    url: https://deckhand/api/v1.0/revisions/1/documents?schema=deckhand/ValidationPolicy/v1&name=site-deploy-validation
    status: failure
    validations:
      - name: deckhand-schema-validation
        url: https://deckhand/api/v1.0/revisions/1/validations/deckhand-schema-validation/0
        status: success
      - name: drydock-site-validation
        status: missing
      - name: promenade-site-validation
        url: https://deckhand/api/v1.0/revisions/1/validations/promenade-site-validation/0
        status: expired
      - name: armada-deployability-validation
        url: https://deckhand/api/v1.0/revisions/1/validations/armada-deployability-validation/0
        status: failure
...
```

Validation status is always for the most recent entry for a given validation.
A status of `missing` indicates that no entries have been created. A status
of `expired` indicates that the validation had succeeded, but the
`expiresAfter` limit specified in the `ValidationPolicy` has been exceeded.

This endpoint uses the `deckhand:show_revision` action.

### GET `/revisions/{{revision_id}}/diff/{{comparison_revision_id}}`

This endpoint provides a basic comparison of revisions in terms of how the
buckets involved have changed.  Only buckets with existing documents in either
of the two revisions in question will be reported; buckets with documents that
are only present in revisions between the two being compared are omitted from
this report. That is, buckets with documents that were accidentally created
(and then deleted to rectify the mistake) that are not directly present in
the two revisions being compared are omitted.

The response will contain a status of `created`, `deleted`, `modified`, or
`unmodified` for each bucket.

The ordering of the two revision ids is not important.

For the purposes of diffing, the `revision_id` "0" is treated as a revision
with no documents, so queries comparing revision "0" to any other revision will
report "created" for each bucket in the compared revision.

Diffing a revision against itself will respond with the each of the buckets in
the revision as `unmodified`.

Diffing revision "0" against itself results in an empty dictionary as the response.

#### Examples
A response for a typical case, `GET /api/v1.0/revisions/6/diff/3` (or
equivalently `GET /api/v1.0/revisions/3/diff/6`).

```yaml
---
bucket_a: created
bucket_b: deleted
bucket_c: modified
bucket_d: unmodified
...
```

A response for diffing against an empty revision, `GET /api/v1.0/revisions/0/diff/6`:

```yaml
---
bucket_a: created
bucket_c: created
bucket_d: created
...
```

A response for diffing a revision against itself, `GET /api/v1.0/revisions/6/diff/6`:

```yaml
---
bucket_a: unmodified
bucket_c: unmodified
bucket_d: unmodified
...
```

Diffing two revisions that contain the same documents, `GET /api/v1.0/revisions/8/diff/11`:

```yaml
---
bucket_e: unmodified
bucket_f: unmodified
bucket_d: unmodified
...
```

Diffing revision zero with itself, `GET /api/v1.0/revisions/0/diff/0`:

```yaml
---
{}
...
```

### POST `/revisions/{{revision_id}}/validations/{{name}}`

Add the results of a validation for a particular revision.

An example `POST` request body indicating validation success:

```yaml
---
status: success
validator:
  name: promenade
  version: 1.1.2
...
```

An example `POST` request indicating validation failure:

```http
POST /api/v1.0/revisions/3/validations/promenade-site-validation
Content-Type: application/x-yaml

---
status: failure
errors:
  - documents:
      - schema: promenade/Node/v1
        name: node-document-name
      - schema: promenade/Masters/v1
        name: kubernetes-masters
    message: Node has master role, but not included in cluster masters list.
validator:
  name: promenade
  version: 1.1.2
...
```

This endpoint uses the `deckhand:create_validation` action.

### GET `/revisions/{{revision_id}}/validations`

Gets the list of validations which have been reported for this revision.

Sample response:

```yaml
---
count: 2
next: null
prev: null
results:
  - name: deckhand-schema-validation
    url: https://deckhand/api/v1.0/revisions/4/validations/deckhand-schema-validation
    status: success
  - name: promenade-site-validation
    url: https://deckhand/api/v1.0/revisions/4/validations/promenade-site-validation
    status: failure
...
```

This endpoint uses the `deckhand:list_validations` action.

### GET `/revisions/{{revision_id}}/validations/{{name}}`

Gets the list of validation entry summaries that have been posted.

Sample response:

```yaml
---
count: 1
next: null
prev: null
results:
  - id: 0
    url: https://deckhand/api/v1.0/revisions/4/validations/promenade-site-validation/0/entries/0
    status: failure
...
```

This endpoint uses the `deckhand:list_validations` action.

### GET `/revisions/{{revision_id}}/validations/{{name}}/entries/{{entry_id}}`

Gets the full details of a particular validation entry, including all posted
error details.

Sample response:

```yaml
---
name: promenade-site-validation
url: https://deckhand/api/v1.0/revisions/4/validations/promenade-site-validation/entries/0
status: failure
createdAt: 2017-07-16T02:03Z
expiresAfter: null
expiresAt: null
errors:
  - documents:
      - schema: promenade/Node/v1
        name: node-document-name
      - schema: promenade/Masters/v1
        name: kubernetes-masters
    message: Node has master role, but not included in cluster masters list.
...
```

This endpoint uses the `deckhand:show_validation` action.

### POST `/revisions/{{revision_id}}/tags/{{tag}}`

Associate the revision with a collection of metadata, if provided, by way of
a tag. The tag itself can be used to label the revision.

Sample request with body:

```http
POST `/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags/foobar`
Content-Type: application/x-yaml

---
metadata:
  - name: foo
    thing: bar
...
```

Sample response:

```http
Content-Type: application/x-yaml
HTTP/1.1 201 Created
Location: https://deckhand/api/v1.0/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags/foobar

---
tag: foobar
metadata:
  - name: foo
    thing: bar
...
```

Sample request without body:

```http
POST `/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags/foobar`
Content-Type: application/x-yaml
```

Sample response:


```http
Content-Type: application/x-yaml
HTTP/1.1 201 Created
Location: https://deckhand/api/v1.0/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags/foobar

---
tag: foobar
...
```

This endpoint uses the `deckhand:create_tag` action.

### GET `/revisions/{{revision_id}}/tags`

List the tags associated with a revision.

Sample request with body:

```http
GET `/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags`
```

Sample response:

```http
Content-Type: application/x-yaml
HTTP/1.1 200 OK

---
- metadata:
  name: foo
  thing: bar
- metadata:
  name: baz
  thing: qux
...
```

This endpoint uses the `deckhand:list_tags` action.

### GET `/revisions/{{revision_id}}/tags/{{tag}}`

Show tag details for tag associated with a revision.

Sample request with body:

```http
GET `/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags/foo`
```

Sample response:

```http
Content-Type: application/x-yaml
HTTP/1.1 200 OK

---
metadata:
  - name: foo
    thing: bar
...
```

This endpoint uses the `deckhand:show_tag` action.

### DELETE `/revisions/{{revision_id}}/tags/{{tag}}`

Delete tag associated with a revision.

Sample request with body:

```http
GET `/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags/foo`
```

Sample response:

```http
Content-Type: application/x-yaml
HTTP/1.1 204 No Content
```

This endpoint uses the `deckhand:delete_tag` action.

### DELETE `/revisions/{{revision_id}}/tags`

Delete all tags associated with a revision.

Sample request with body:

```http
GET `/revisions/0615b731-7f3e-478d-8ba8-a223eab4757e/tags`
```

Sample response:

```http
Content-Type: application/x-yaml
HTTP/1.1 204 No Content
```

This endpoint uses the `deckhand:delete_tags` action.

### POST `/rollback/{target_revision_id}`

Creates a new revision that contains exactly the same set of documents as the
revision specified by `target_revision_id`.

This endpoint uses the `deckhand:create_cleartext_documents` and
`deckhand:create_encrypted_documents` actions.
