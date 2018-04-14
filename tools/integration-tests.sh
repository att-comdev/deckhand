#!/usr/bin/env bash

# Script intended for running Deckhand integration tests, where integration
# is defined as the interaction between Deckhand and Keystone and Barbican.
# Installation dependency is openstack-helm-infra.

# TODO(fmontei): Use Ansible for all this.

set -xe

# Install required packages.
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

# Clone openstack-helm-infra and setup host and k8s.
CURRENT_DIR="$(pwd)"
: ${OSH_INFRA_PATH:="../openstack-helm-infra"}
: ${OSH_PATH:="../openstack-helm"}

if [ ! -d "$OSH_INFRA_PATH" ]; then
    git clone https://git.openstack.org/openstack/openstack-helm-infra.git ../
    git clone https://git.openstack.org/openstack/openstack-helm.git ../
fi

cd ${OSH_INFRA_PATH}
make dev-deploy setup-host
make dev-deploy k8s

cd ${OSH_PATH}
# Setup clients on the host and assemble the charts¶
./tools/deployment/developer/common/020-setup-client.sh
# Deploy the ingress controller
./tools/deployment/developer/common/030-ingress.sh
# Deploy NFS Provisioner
./tools/deployment/developer/nfs/040-nfs-provisioner.sh
# Deploy MariaDB
./tools/deployment/developer/nfs/050-mariadb.sh
# Deploy RabbitMQ
./tools/deployment/developer/nfs/060-rabbitmq.sh
# Deploy Memcached
./tools/deployment/developer/nfs/070-memcached.sh
# Deploy Keystone
./tools/deployment/developer/nfs/080-keystone.sh

# Deploy Barbican.
# Pull images and lint chart
make pull-images barbican

# Deploy command
: ${OSH_EXTRA_HELM_ARGS:=""}
helm upgrade --install barbican ./barbican \
    --namespace=openstack \
    ${OSH_EXTRA_HELM_ARGS} \
    ${OSH_EXTRA_HELM_ARGS_HORIZON}

# Wait for deploy
./tools/deployment/common/wait-for-pods.sh openstack

# Validate deployment info
helm status barbican

cd ${CURRENT_DIR}
# TODO(fmontei): Deploy PostgreSQL and Deckhand.
# TODO(fmontei): Run tests.
