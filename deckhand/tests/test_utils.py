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

import functools
import inspect
import os
import random
import uuid
import yaml

from oslo_serialization import jsonutils as json


def rand_uuid_hex():
    """Generate a random UUID hex string

    :return: a random UUID (e.g. '0b98cf96d90447bda4b46f31aeb1508c')
    :rtype: string
    """
    return uuid.uuid4().hex


def rand_name(name='', prefix='deckhand'):
    """Generate a random name that includes a random number

    :param str name: The name that you want to include
    :param str prefix: The prefix that you want to include
    :return: a random name. The format is
             '<prefix>-<name>-<random number>'.
             (e.g. 'prefixfoo-namebar-154876201')
    :rtype: string
    """
    randbits = str(random.randint(1, 0x7fffffff))
    rand_name = randbits
    if name:
        rand_name = name + '-' + rand_name
    if prefix:
        rand_name = prefix + '-' + rand_name
    return rand_name


def rand_bool():
    """Generate a random boolean value.

    :return: a random boolean value.
    :rtype: boolean
    """
    return random.choice([True, False])


def rand_int(min, max):
    """Generate a random integer value between range (`min`, `max`).

    :return: a random integer between the range(`min`, `max`).
    :rtype: integer
    """
    return random.randint(min, max)


def file_data(file_path):
    """Read file data and pass the dictionary representation into the test.

    Should be added to methods of instances of ``unittest.TestCase``.

    ``file_path`` should be a path relative to the directory of the file
    containing the decorated ``unittest.TestCase``. The file
    should contain JSON- or YAML-encoded data.

    :param file_path: Path to a test resource file.
    :raises TypeError: If the ``file_path`` extension is not .yml, .yaml or
        .json.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *func_args, **func_kwargs):
            test_loc = inspect.getmodule(f).__package__.replace('.', '/')
            abs_file_path = os.path.join(test_loc, file_path)
            file_ext = os.path.splitext(file_path)[1]

            with open(abs_file_path) as file:
                file_data = file.read()

            if file_ext in ['.yml', '.yaml']:
                resource_data = yaml.safe_load(file_data)
            elif file_ext in ['.json']:
                resource_data = json.loads(file_data)
            else:
                raise TypeError('The provided file %s must end in %s.' %
                                (file_path, ['.yml', '.yaml', '.json']))

            return f(self, resource_data, *func_args, **func_kwargs)
        return wrapper
    return decorator
