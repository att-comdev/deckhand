# Copyright 2018 AT&T Intellectual Property.  All other rights reserved.
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

from oslo_cache import core as cache

from deckhand.conf import config

CONF = config.CONF

cache.configure(CONF)


def create_region(name):
    """Create a dogile region."""
    region = cache.create_region()
    region.name = name  # oslo.cache doesn't allow this yet
    return region


CACHE_REGION = create_region(name='shared default')


def configure_cache(region=None):
    if region is None:
        region = CACHE_REGION
    cache.configure_cache_region(CONF, region)


def get_memoization_decorator(group, expiration_group=None, region=None):
    if region is None:
        region = CACHE_REGION
    return cache.get_memoization_decorator(CONF, region, group,
                                           expiration_group=expiration_group)
