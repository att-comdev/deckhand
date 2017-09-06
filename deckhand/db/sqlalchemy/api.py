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


"""Defines interface for DB access."""

import ast
import copy
import functools
import threading

from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_db import options
from oslo_db.sqlalchemy import session
from oslo_log import log as logging
from oslo_serialization import jsonutils as json
import six
import sqlalchemy.orm as sa_orm

from deckhand.db.sqlalchemy import models
from deckhand import errors
from deckhand import types
from deckhand import utils

sa_logger = None
LOG = logging.getLogger(__name__)

CONF = cfg.CONF

options.set_defaults(CONF)

_FACADE = None
_LOCK = threading.Lock()


def _retry_on_deadlock(exc):
    """Decorator to retry a DB API call if Deadlock was received."""

    if isinstance(exc, db_exception.DBDeadlock):
        LOG.warn("Deadlock detected. Retrying...")
        return True
    return False


def _create_facade_lazily():
    global _LOCK, _FACADE
    if _FACADE is None:
        with _LOCK:
            if _FACADE is None:
                _FACADE = session.EngineFacade.from_config(
                    CONF, sqlite_fk=True)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(autocommit=True, expire_on_commit=False):
    facade = _create_facade_lazily()
    return facade.get_session(autocommit=autocommit,
                              expire_on_commit=expire_on_commit)


def clear_db_env():
    """Unset global configuration variables for database."""
    global _FACADE
    _FACADE = None


def setup_db():
    models.register_models(get_engine())


def drop_db():
    models.unregister_models(get_engine())


def documents_create(bucket_name, documents, validation_policies,
                     session=None):
    session = session or get_session()

    documents_created = _documents_create(documents, session)
    val_policies_created = _documents_create(validation_policies, session)
    all_docs_created = documents_created + val_policies_created

    if all_docs_created:
        bucket = bucket_get_or_create(bucket_name)
        revision = revision_create()

        for doc in all_docs_created:
            with session.begin():
                doc['bucket_id'] = bucket['name']
                doc['revision_id'] = revision['id']
                doc.save(session=session)

    return [d.to_dict() for d in documents_created]


def _documents_create(values_list, session=None):
    """Create a set of documents and associated schema.

    If no changes are detected, a new revision will not be created. This
    allows services to periodically re-register their schemas without
    creating unnecessary revisions.

    :param values_list: List of documents to be saved.
    """
    values_list = copy.deepcopy(values_list)
    session = session or get_session()
    filters = models.Document.UNIQUE_CONSTRAINTS

    do_create = False
    documents_created = []

    def _document_changed(existing_document):
        # The document has changed if at least one value in ``values`` differs.
        for key, val in values.items():
            if val != existing_document[key]:
                return True
        return False

    def _get_model(schema):
        if schema == types.VALIDATION_POLICY_SCHEMA:
            return models.ValidationPolicy()
        else:
            return models.Document()

    def _document_create(values):
        document = _get_model(values['schema'])
        with session.begin():
            document.update(values)
        return document

    for values in values_list:
        values['_metadata'] = values.pop('metadata')
        values['name'] = values['_metadata']['name']

        try:
            existing_document = document_get(
                raw_dict=True,
                **{c: values[c] for c in filters if c != 'revision_id'})
        except errors.DocumentNotFound:
            # Ignore bad data at this point. Allow creation to bubble up the
            # error related to bad data.
            existing_document = None

        if not existing_document:
            do_create = True
        elif existing_document and _document_changed(existing_document):
            do_create = True

    if do_create:
        for values in values_list:
            doc = _document_create(values)
            documents_created.append(doc)

    return documents_created


def document_get(session=None, raw_dict=False, **filters):
    session = session or get_session()

    # Retrieve the most recently created version of a document. Documents with
    # the same metadata.name and schema can exist across different revisions,
    # so it is necessary to use `first` instead of `one` to avoid errors.
    document = session.query(models.Document)\
        .filter_by(**filters)\
        .order_by(models.Document.created_at.desc())\
        .first()

    if not document:
        raise errors.DocumentNotFound(document=filters)

    return document.to_dict(raw_dict=raw_dict)


####################


def bucket_get_or_create(bucket_name, session=None):
    session = session or get_session()

    try:
        bucket = session.query(models.Bucket)\
            .filter_by(name=bucket_name)\
            .one()
    except sa_orm.exc.NoResultFound:
        bucket = models.Bucket()
        with session.begin():
            bucket.update({'name': bucket_name})
            bucket.save(session=session)

    return bucket.to_dict()


####################

def revision_create(session=None):
    session = session or get_session()

    revision = models.Revision()
    with session.begin():
        revision.save(session=session)

    return revision.to_dict()


def revision_get(revision_id, session=None):
    """Return the specified `revision_id`.

    :raises: RevisionNotFound if the revision was not found.
    """
    session = session or get_session()

    try:
        revision = session.query(models.Revision)\
            .filter_by(id=revision_id)\
            .one()
    except sa_orm.exc.NoResultFound:
        raise errors.RevisionNotFound(revision=revision_id)

    return revision.to_dict()


def require_revision_exists(f):
    """Decorator to require the specified revision to exist.
    Requires the wrapped function to use revision_id as the first argument.
    """

    @functools.wraps(f)
    def wrapper(revision_id, *args, **kwargs):
        revision_get(revision_id)
        return f(revision_id, *args, **kwargs)
    return wrapper


def revision_get_all(session=None):
    """Return list of all revisions."""
    session = session or get_session()
    revisions = session.query(models.Revision)\
        .all()
    return [r.to_dict() for r in revisions]


def revision_delete_all(session=None):
    """Delete all revisions."""
    session = session or get_session()
    session.query(models.Revision)\
        .delete(synchronize_session=False)


def revision_get_documents(revision_id, session=None, include_history=False,
                           **filters):
    """Return the documents that match filters for the specified `revision_id`.

    Deleted documents are not included unless deleted=True is provided in
    ``filters``.

    :param revision_id: The ID corresponding to the ``Revision`` object.
    :param session: Database session object.
    :param include_history: Return all documents for revision history prior
        and up to current revision, if ``True``.
    :raises: RevisionNotFound if the revision was not found.
    """
    session = session or get_session()
    revision_documents = []

    try:
        revision = session.query(models.Revision)\
            .filter_by(id=revision_id)\
            .one()
        revision_documents = revision.to_dict()['documents'] or []

        if include_history:
            older_revisions = session.query(models.Revision)\
                .filter(models.Revision.created_at < revision.created_at)\
                .order_by(models.Revision.created_at)\
                .all()

            # Include documents from older revisions in response body.
            for older_revision in older_revisions:
                revision_documents.extend(
                    older_revision.to_dict()['documents'])
    except sa_orm.exc.NoResultFound:
        raise errors.RevisionNotFound(revision=revision_id)

    filtered_documents = _filter_revision_documents(
        revision_documents, **filters)

    return filtered_documents


def _filter_revision_documents(documents, **filters):
    """Return the list of documents that match filters.

    :returns: List of documents that match specified filters.
    """
    # TODO(fmontei): Implement this as an sqlalchemy query.
    filtered_documents = []

    for document in documents:
        match = True

        for filter_key, filter_val in filters.items():
            actual_val = utils.multi_getattr(filter_key, document)

            if (isinstance(actual_val, bool)
                and isinstance(filter_val, six.string_types)):
                try:
                    filter_val = ast.literal_eval(filter_val.title())
                except ValueError:
                    # If not True/False, set to None to avoid matching
                    # `actual_val` which is always boolean.
                    filter_val = None

            if actual_val != filter_val:
                match = False

        if match:
            filtered_documents.append(document)

    return filtered_documents


def revision_diff_get(revision_id, comparison_revision_id):
    """Generate the diff between two revisions.

    Generate the diff between the two revisions `revision_id` and
    `comparison_revision_id`. A basic comparison of the revisions in terms of
    how the buckets involved have changed is generated. Only buckets with
    existing documents in either of the two revisions in question will be
    reported.

    The ordering of the two revision ids is not important.

    The differences include:

        - "created": A bucket has been created between the revisions.
        - "deleted": A bucket has been deleted between the revisions.
        - "modified": A bucket has been modified between the revisions.
        - "unmodified": A bucket remains unmodified between the revisions.

    :param revision_id: ID of the first revision.
    :param comparison_revision_id: ID of the second revision.
    :returns: A dictionary, keyed with the bucket IDs, containing any of the
        differences enumerated above.

    Examples::

        # GET /api/v1.0/revisions/6/diff/3
        bucket_a: created
        bucket_b: deleted
        bucket_c: modified
        bucket_d: unmodified

        # GET /api/v1.0/revisions/0/diff/6
        bucket_a: created
        bucket_c: created
        bucket_d: created

        # GET /api/v1.0/revisions/6/diff/6
        bucket_a: unmodified
        bucket_c: unmodified
        bucket_d: unmodified

        # GET /api/v1.0/revisions/0/diff/0
        {}
    """
    # Retrieve document history for each revision. Since `revision_id` of 0
    # doesn't exist, treat it as a special case: empty list.
    docs = (revision_get_documents(revision_id, include_history=True)
            if revision_id != 0 else [])
    comparison_docs = (revision_get_documents(comparison_revision_id,
                                              include_history=True)
                       if comparison_revision_id != 0 else [])

    revision = revision_get(revision_id) if revision_id != 0 else None
    comparison_revision = (revision_get(comparison_revision_id)
                           if comparison_revision_id != 0 else None)

    # Each dictionary below, keyed with the bucket's name, references the list
    # of documents related to each bucket.
    buckets = {}
    comparison_buckets = {}
    for doc in docs:
        buckets.setdefault(doc['bucket_id'], [])
        buckets[doc['bucket_id']].append(doc)
    for doc in comparison_docs:
        comparison_buckets.setdefault(doc['bucket_id'], [])
        comparison_buckets[doc['bucket_id']].append(doc)

    # Exclude buckets that have no shared documents in either `revision_id` or
    # `comparison_revision_id`.
    if not (revision_id == 0 or comparison_revision_id == 0):
        endpoint_revision_docs = {(d['name'], d['schema']) for d in docs
                                   if d['revision_id'] == revision_id}
        endpoint_revision_docs.union(
            {(d['name'], d['schema']) for d in comparison_docs
              if d['revision_id'] == revision_id})

        # Exclude buckets belonging to `revision_id`.
        for bucket_name, bucket_docs in copy.copy(buckets).items():
            found = False
            for d in bucket_docs:
                if (d['name'], d['schema']) in endpoint_revision_docs:
                    found = True
                    break
            if not found:
                buckets.pop(bucket_name, None)

        # Exclude buckets belonging to `comparison_revision_id`.
        for bucket_name, bucket_docs in copy.copy(comparison_buckets).items():
            found = False
            for d in bucket_docs:
                if (d['name'], d['schema']) in endpoint_revision_docs:
                    found = True
                    break
            if not found:
                comparison_buckets.pop(bucket_name, None)

    # `shared_buckets` references buckets shared by both `revision_id` and
    # `comparison_revision_id` -- i.e. their intersection.
    shared_buckets = set(buckets.keys()).intersection(
        comparison_buckets.keys())
    # `unshared_buckets` references buckets not shared by both `revision_id`
    # and `comparison_revision_id` -- i.e. their non-intersection.
    unshared_buckets = set(buckets.keys()).union(
        comparison_buckets.keys()) - shared_buckets

    result = {}

    def _compare_buckets(b1, b2):
        # Checks whether buckets' documents are identical.
        json_b1 = []
        json_b2 = []

        for d in b1:
            json_b1.append(json.dumps(d, sort_keys=True))
        for d in b2:
            json_b2.append(json.dumps(d, sort_keys=True))

        return sorted(json_b1) == sorted(json_b2)

    # If the list of documents for each bucket is indentical, then the result
    # is "unmodified", else "modified".
    for bucket_id in shared_buckets:
        unmodified = _compare_buckets(buckets[bucket_id],
                                      comparison_buckets[bucket_id])
        result[bucket_id] = 'unmodified' if unmodified else 'modified'

    for bucket_id in unshared_buckets:
        # If neither revision has documents, then there's nothing to compare.
        # This is always True for revision_id == comparison_revision_id == 0.
        if not any([revision, comparison_revision]):
            break
        # Else if one revision == 0 and the other revision != 0, then the
        # bucket has been created. Which is zero or non-zero doesn't matter.
        elif not all([revision, comparison_revision]):
            result[bucket_id] = 'created'
        # Else if `revision` is newer than `comparison_revision`, then if the
        # `bucket_id` isn't in the `revision` buckets, then it has been
        # deleted. Otherwise it has been created.
        elif revision['created_at'] > comparison_revision['created_at']:
            if bucket_id not in buckets:
                result[bucket_id] = 'deleted'
            elif bucket_id not in comparison_buckets:
                result[bucket_id] = 'created'
        # Else if `comparison_revision` is newer than `revision`, then if the
        # `bucket_id` isn't in the `revision` buckets, then it has been
        # created. Otherwise it has been deleted.
        else:
            if bucket_id not in buckets:
                result[bucket_id] = 'created'
            elif bucket_id not in comparison_buckets:
                result[bucket_id] = 'deleted'

    return result


####################


@require_revision_exists
def revision_tag_create(revision_id, tag, data=None, session=None):
    """Create a revision tag.

    :returns: The tag that was created if not already present in the database,
        else None.
    """
    session = session or get_session()
    tag_model = models.RevisionTag()

    try:
        assert not data or isinstance(data, dict)
    except AssertionError:
        raise errors.RevisionTagBadFormat(data=data)

    try:
        with session.begin():
            tag_model.update(
                {'tag': tag, 'data': data, 'revision_id': revision_id})
            tag_model.save(session=session)
        resp = tag_model.to_dict()
    except db_exception.DBDuplicateEntry:
        resp = None

    return resp


@require_revision_exists
def revision_tag_get(revision_id, tag, session=None):
    """Retrieve tag details.

    :returns: None
    :raises RevisionTagNotFound: If ``tag`` for ``revision_id`` was not found.
    """
    session = session or get_session()

    try:
        tag = session.query(models.RevisionTag)\
            .filter_by(tag=tag, revision_id=revision_id)\
            .one()
    except sa_orm.exc.NoResultFound:
        raise errors.RevisionTagNotFound(tag=tag, revision=revision_id)

    return tag.to_dict()


@require_revision_exists
def revision_tag_get_all(revision_id, session=None):
    """Return list of tags for a revision.

    :returns: List of tags for ``revision_id``, ordered by the tag name by
        default.
    """
    session = session or get_session()
    tags = session.query(models.RevisionTag)\
        .filter_by(revision_id=revision_id)\
        .order_by(models.RevisionTag.tag)\
        .all()
    return [t.to_dict() for t in tags]


@require_revision_exists
def revision_tag_delete(revision_id, tag, session=None):
    """Delete a specific tag for a revision.

    :returns: None
    """
    session = session or get_session()
    result = session.query(models.RevisionTag)\
                .filter_by(tag=tag, revision_id=revision_id)\
                .delete(synchronize_session=False)
    if result == 0:
        raise errors.RevisionTagNotFound(tag=tag, revision=revision_id)


@require_revision_exists
def revision_tag_delete_all(revision_id, session=None):
    """Delete all tags for a revision.

    :returns: None
    """
    session = session or get_session()
    session.query(models.RevisionTag)\
        .filter_by(revision_id=revision_id)\
        .delete(synchronize_session=False)
