#!/usr/bin/env bash

# Script intended for running Deckhand integration tests, where integration
# is defined as the interaction between Deckhand and Keystone and Barbican.
# Installation dependency is openstack-helm-infra.
#
# USAGE: ./tools/integration-tests.sh <test-regex>

# TODO(fmontei): Use Ansible for all this.
# NOTE(fmontei): May have to automate the following installation guide for CI:
# https://docs.openstack.org/openstack-helm/latest/install/developer/requirements-and-host-config.html#host-configuration

set -xe

DECKHAND_IMAGE=${DECKHAND_IMAGE:-}

CURRENT_DIR="$(pwd)"
: ${OSH_INFRA_PATH:="../openstack-helm-infra"}
: ${OSH_PATH:="../openstack-helm"}


function cleanup_deckhand {
    set +e

    if [ -n "$POSTGRES_ID" ]; then
        sudo docker stop $POSTGRES_ID
    fi

    if [ -n "$DECKHAND_ID" ]; then
        sudo docker stop $DECKHAND_ID
    fi

    rm -rf $CONF_DIR

    if [ -z "$DECKHAND_IMAGE" ]; then
        # Kill all processes and child processes (for example, if workers > 1)
        # if using uwsgi only.
        PGID=$(ps -o comm -o pgid | grep uwsgi | grep -o [0-9]* | head -n 1)
        if [ -n "$PGID" ]; then
            setsid kill -- -$PGID
        fi
    fi
}


function cleanup_osh {
    set +e

    if [ -n "command -v kubectl" ]; then
        kubectl delete namespace openstack
        kubectl delete namespace ucp
    fi

    sudo systemctl disable kubelet --now
    sudo systemctl stop kubelet

    if [ -n "command -v docker" ]; then
        sudo docker ps -aq | xargs -L1 -P16 sudo docker rm -f
    fi

    sudo rm -rf /var/lib/openstack-helm
}


function install_deps {
    set -xe

    # NOTE(fmontei): While as a part of `make setup-host` below some of
    # these dependencies are installed, we want Deckhand to idempotently
    # install everything it needs for the foregoing to work.
    sudo apt-get update
    sudo apt-get install --no-install-recommends -y \
            ca-certificates \
            git \
            make \
            jq \
            nmap \
            curl \
            uuid-runtime \
            ipcalc \
            python-pytest \
            python-pip
    # NOTE(fmontei): Use this version because newer versions might
    # be slightly different in terms of test syntax in YAML files.
    sudo -H -E pip install gabbi==1.35.1 \
        stestr
}


function deploy_barbican {
    set -xe

    # Pull images and lint chart
    make pull-images barbican

    # Deploy command
    helm upgrade --install barbican ./barbican \
        --namespace=openstack

    # Wait for deploy
    ./tools/deployment/common/wait-for-pods.sh openstack

    # Validate deployment info
    helm status barbican
}


function deploy_osh_keystone_barbican {
    set -xe

    trap cleanup_osh EXIT

    if [ ! -d "$OSH_INFRA_PATH" ]; then
        git clone https://git.openstack.org/openstack/openstack-helm-infra.git ../openstack-helm-infra
    fi

    if [ ! -d "$OSH_PATH" ]; then
        git clone https://git.openstack.org/openstack/openstack-helm.git ../openstack-helm
    fi

    cd ${OSH_INFRA_PATH}
    # NOTE(fmontei): setup-host already sets up required host dependencies.
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
    set -xe

    trap cleanup_deckhand EXIT

    export OS_CLOUD=openstack_helm

    cd ${CURRENT_DIR}

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
    gen_paste false

    # NOTE(fmontei): Generate an admin token instead of hacking a policy
    # file with no permissions to test authN as well as authZ.
    set +x
    export TEST_AUTH_TOKEN=$( openstack token issue --format value -c id )
    set -x
    export TEST_BARBICAN_URL=$( openstack endpoint list --format value | grep barbican | grep public | awk '{print $7}' )

    if [ -z "$DECKHAND_IMAGE" ]; then
        log_section "Running Deckhand via uwsgi."

        alembic upgrade head
        # NOTE(fmontei): Deckhand's database is not configured to work with
        # multiprocessing. Currently there is a data race on acquiring shared
        # SQLAlchemy engine pooled connection strings when workers > 1. As a
        # workaround, we use multiple threads but only 1 worker. For more
        # information, see: https://github.com/att-comdev/deckhand/issues/20
        export DECKHAND_API_WORKERS=1
        export DECKHAND_API_THREADS=4
        source entrypoint.sh server &
    else
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

        DECKHAND_ID=$(sudo docker ps | grep deckhand | awk '{print $1}')
        echo $DECKHAND_ID
    fi

    # Give the server a chance to come up. Better to poll a health check.
    sleep 5
}


function run_tests {
    set +e

    export DECKHAND_TESTS_DIR=${CURRENT_DIR}/deckhand/tests/integration/gabbits

    posargs=$@
    if [ ${#posargs} -ge 1 ]; then
        py.test -k $1 -svx ${CURRENT_DIR}/deckhand/tests/common/test_gabbi.py
    else
        py.test -svx  ${CURRENT_DIR}/deckhand/tests/common/test_gabbi.py
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

install_deps

# Clone openstack-helm-infra and setup host and k8s.
deploy_osh_keystone_barbican

# Deploy PostgreSQL and Deckhand.
deploy_postgre
deploy_deckhand

run_tests "$@"
