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

from . import errors
from .document import CompleteDocument
import jsonschema
import logging
import os
import pkg_resources
import yaml

__all__ = ['get_owned_schemas', 'structural', 'validate_data']

LOG = logging.getLogger(__name__)

STRUCTURAL_SCHEMAS = {}

DATA_SCHEMAS = {}


def get_owned_schemas():
    return list(DATA_SCHEMAS.values())


def validate_data(doc, schema):
    try:
        jsonschema.validate(doc.data, schema.data)
    except jsonschema.exceptions.ValidationError as e:
        return [errors.DataValidationError('%s: %r' % (doc.full_name, e))]


def structural(document, layering_policy):
    structural_data = document.as_dict_for_root_validation
    try:
        jsonschema.validate(structural_data, STRUCTURAL_SCHEMAS['root'])
    except jsonschema.exceptions.ValidationError as e:
        return [errors.StructuralValidationError(e)]

    try:
        metadata = structural_data['metadata']
        metadata_schema = metadata['schema']
        jsonschema.validate(metadata, STRUCTURAL_SCHEMAS[metadata_schema])
    except jsonschema.exceptions.ValidationError as e:
        return [
            errors.MetadataValidationError('%s: %r' % (document.full_name, e))
        ]


def _load_data_schemas():
    global DATA_SCHEMAS
    top_dir = pkg_resources.resource_filename('deckhand',
                                              'engine/v2/schemas/data')
    for root, _dirs, filenames in os.walk(top_dir):
        for filename in filenames:
            abs_path = os.path.join(root, filename)
            schema_name, _ext = os.path.splitext(
                os.path.relpath(abs_path, top_dir))
            LOG.debug('Loading data schema "%s" from "%s"', schema_name,
                      abs_path)
            with open(abs_path) as f:
                doc = CompleteDocument(yaml.safe_load(f))
                LOG.debug('Loaded document %s', doc.full_name)
                DATA_SCHEMAS[doc.name] = doc


def _load_structural_schemas():
    global STRUCTURAL_SCHEMAS
    top_dir = pkg_resources.resource_filename('deckhand',
                                              'engine/v2/schemas/structural')
    root_schema_path = os.path.join(top_dir, 'root.yaml')
    LOG.debug('Loading root structural schema from %s', root_schema_path)
    with open(root_schema_path) as f:
        STRUCTURAL_SCHEMAS['root'] = CompleteDocument(yaml.safe_load(f)).data
    for root, _dirs, filenames in os.walk(top_dir):
        if root != top_dir:
            for filename in filenames:
                abs_path = os.path.join(root, filename)
                schema_name, _ext = os.path.splitext(
                    os.path.relpath(abs_path, top_dir))
                LOG.debug('Loading metadata schema "%s" from "%s"',
                          schema_name, abs_path)
                with open(abs_path) as f:
                    doc = CompleteDocument(yaml.safe_load(f))
                    LOG.debug('Loaded document %s', doc.full_name)
                    STRUCTURAL_SCHEMAS[doc.name] = doc.data


_load_data_schemas()
_load_structural_schemas()
