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
from . import path
import logging

LOG = logging.getLogger(__name__)


def apply(document, source_list):
    sub_errors = []
    result = document

    sources = {(s.schema, s.name): s for s in source_list}

    for sub in document.substitutions:
        src = sub['src']
        dest = sub['dest']
        source = sources[(src['schema'], src['name'])]
        source_data, extract_errors = path.extract(source, src['path'])
        if extract_errors:
            sub_errors.extend(extract_errors)
            break

        result, inject_errors = path.inject(
            result, source_data, dest['path'], pattern=dest.get('pattern'))
        if inject_errors:
            sub_errors.extend(inject_errors)
            break

    if not sub_errors:
        return result, []
    else:
        return None, [errors.SubstitutionError(causes=sub_errors)]
