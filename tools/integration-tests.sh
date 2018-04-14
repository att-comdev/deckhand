#!/usr/bin/env bash

# Script intended for running Deckhand integration tests, where integration
# is defined as the interaction between Deckhand and Keystone and Barbican.
# Installation dependency is openstack-helm-infra.

# TODO(fmontei): Use Ansible for all this.
# NOTE(fmontei): May have to automate the following installation guide for CI:
# https://docs.openstack.org/openstack-helm/latest/install/developer/requirements-and-host-config.html#host-configuration

set -xe

DECKHAND_IMAGE=${DECKHAND_IMAGE:-quay.io/attcomdev/deckhand:latest}

CURRENT_DIR="$(pwd)"
: ${OSH_INFRA_PATH:="../openstack-helm-infra"}
: ${OSH_PATH:="../openstack-helm"}


function install_deps {
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
}


function deploy_barbican {
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
}


function deploy_osh_keystone_barbican {
    if [ ! -d "$OSH_INFRA_PATH" ]; then
        git clone https://git.openstack.org/openstack/openstack-helm-infra.git ../openstack-helm-infra
    fi

    if [ ! -d "$OSH_PATH" ]; then
        git clone https://git.openstack.org/openstack/openstack-helm.git ../openstack-helm
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

    deploy_barbican
}


function deploy_deckhand {
    # TODO(fmontei): Use Keystone bootstrap override instead.
    interfaces=("admin" "public" "internal")
    deckhand_endpoint="http://127.0.0.1:9000"

    if [ -z "$( openstack service list --format value | grep deckhand )" ]; then
        openstack service create --enable --name deckhand deckhand
    fi

    for iface in ${interfaces[@]}; do
        if [ -z "$( openstack endpoint list --format value | grep deckhand | grep $iface )" ]; then
            openstack endpoint create --enable \
                --region RegionOne \
                deckhand $iface $deckhand_endpoint/api/v1.0
        fi
    done

    openstack service list | grep deckhand
    openstack endpoint list | grep deckhand

    gen_config $deckhand_endpoint
    gen_paste
    gen_policy

    export TEST_AUTH_TOKEN=$( openstack token issue --format value -c id )
    export TEST_BARBICAN_URL=$( openstack endpoint list --format value | grep barbican | grep public | awk '{print $7}' )
    echo $TEST_AUTH_TOKEN

    log_section "Running Deckhand via Docker"
    sudo docker run \
        --rm \
        --net=host \
        -v $CONF_DIR:/etc/deckhand \
        $DECKHAND_IMAGE alembic upgrade head &
    sudo docker run \
        --rm \
        --net=host \
        -p 9000:9000 \
        -v $CONF_DIR:/etc/deckhand \
        $DECKHAND_IMAGE server &

    # Give the server a chance to come up. Better to poll a health check.
    sleep 5

    DECKHAND_ID=$(sudo docker ps | grep deckhand | awk '{print $1}')
    echo $DECKHAND_ID
}


function run_tests {
    set +e

    posargs=$@
    if [ ${#posargs} -ge 1 ]; then
        py.test -k $1 -svx ${CURRENT_DIR}/deckhand/tests/integration/test_gabbi.py
    else
        py.test -svx ${CURRENT_DIR}/deckhand/tests/integration/test_gabbi.py
    fi
    TEST_STATUS=$?

    set -e

    if [ "x$TEST_STATUS" = "x0" ]; then
        log_section Done SUCCESS
    else
        log_section Done FAILURE
        exit $TEST_STATUS
    fi
}


source ${CURRENT_DIR}/tools/common-tests.sh

# Install required packages.
#install_deps

# Clone openstack-helm-infra and setup host and k8s.
#deploy_osh_keystone_barbican

# Deploy PostgreSQL and Deckhand.
deploy_postgre
deploy_deckhand

run_tests "$@"
