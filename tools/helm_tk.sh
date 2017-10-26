#!/bin/bash
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
#
# Script to setup helm-toolkit and helm dep up the deckhand chart
#
HELM=$1

set -x
if [ ! -d build ]; then mkdir build; fi
cd build
git clone https://git.openstack.org/openstack/openstack-helm.git
cd openstack-helm
${HELM} init --client-only
${HELM} serve &
${HELM} repo add local http://localhost:8879/charts
${HELM} repo remove stable
make helm-toolkit
${HELM} dep up ../../charts/deckhand
