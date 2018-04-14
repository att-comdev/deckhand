#!/usr/bin/env bash

# Script intended for running Deckhand integration tests, where integration
# is defined as the interaction between Deckhand and Keystone and Barbican.
# Functional test driver is gabbi. Installation dependency is
# openstack-helm-infra.

# Clone openstack-helm-infra and setup host and k8s.
set -xe

sudo apt-get update
sudo apt-get install --no-install-recommends -y \
        ca-certificates \
        git \
        make \
        jq \
        nmap \
        curl \
        uuid-runtime \
        ipcalc

CURRENT_DIR="$(pwd)"
: ${OSH_INFRA_PATH:="../openstack-helm-infra"}

if [ ! -d "$OSH_INFRA_PATH" ]; then
    git clone https://git.openstack.org/openstack/openstack-helm-infra.git ../
    git clone https://git.openstack.org/openstack/openstack-helm.git ../
fi

cd ${OSH_INFRA_PATH}
make dev-deploy setup-host
make dev-deploy k8s
cd ${CURRENT_DIR}

