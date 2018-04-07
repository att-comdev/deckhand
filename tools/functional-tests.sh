#!/usr/bin/env bash

# Script intended for running Deckhand functional tests via gabbi. Requires
# Docker CE (at least) to run.

set -xe
ROOTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Meant for capturing output of Deckhand image. This requires that logging
# in the image be set up to pipe everything out to stdout/stderr.
STDOUT=$(mktemp)

# NOTE(fmontei): `DECKHAND_IMAGE` should only be specified if the desire is to
# run Deckhand functional tests against a specific Deckhand image, which is
# useful for CICD (as validating the image is vital). However, if the
# `DECKHAND_IMAGE` is not specified, then this implies that the most current
# version of the code should be used, which is in the repo itself.
DECKHAND_IMAGE=${DECKHAND_IMAGE:-}
ROOTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source $ROOTDIR/common-tests.sh


function cleanup_deckhand {
    set +e

    if [ -n "$POSTGRES_ID" ]; then
        sudo docker stop $POSTGRES_ID
    fi
    if [ -n "$DECKHAND_ID" ]; then
        sudo docker stop $DECKHAND_ID
    fi
    if [ -d "$CONF_DIR" ]; then
        rm -rf $CONF_DIR
    fi

    # Kill all processes and child processes (for example, if workers > 1)
    # if using uwsgi only.
    PGID=$(ps -o comm -o pgid | grep uwsgi | grep -o [0-9]* | head -n 1)
    if [ -n "$PGID" ]; then
        setsid kill -- -$PGID
    fi
}
if [ -z "$DECKHAND_IMAGE" ]; then
    RUN_WITH_UWSGI=true
else
    RUN_WITH_UWSGI=false
fi

set -ex

CONF_DIR=$(mktemp -d -p $(pwd))
sudo chmod 777 -R $CONF_DIR

function log_section {
    set +x
    echo 1>&2
    echo 1>&2
    echo === $* === 1>&2
    set -x
}

function cleanup {
    sudo docker stop $POSTGRES_ID

    if [ -n "$DECKHAND_ID" ]; then
        sudo docker stop $DECKHAND_ID
    fi

    if [ -n "$DECKHAND_ALEMBIC_ID" ]; then
        sudo docker stop $DECKHAND_ALEMBIC_ID
    fi

    rm -rf $CONF_DIR

    if $RUN_WITH_UWSGI; then
        # Kill all processes and child processes (for example, if workers > 1)
        # if using uwsgi only.
        PGID=$(ps -o comm -o pgid | grep uwsgi | grep -o [0-9]* | head -n 1)
        setsid kill -- -$PGID
    fi
}


trap cleanup_deckhand EXIT
trap cleanup EXIT


POSTGRES_ID=$(
    sudo docker run \
        --detach \
        --publish :5432 \
        -e POSTGRES_DB=deckhand \
        -e POSTGRES_USER=deckhand \
        -e POSTGRES_PASSWORD=password \
            postgres:9.5
)

POSTGRES_IP=$(
    sudo docker inspect \
        --format='{{ .NetworkSettings.Networks.bridge.IPAddress }}' \
            $POSTGRES_ID
)


function gen_config {
    log_section Creating config file

    export DECKHAND_TEST_URL=http://localhost:9000
    export DATABASE_URL=postgresql+psycopg2://deckhand:password@$POSTGRES_IP:5432/deckhand

    # Used by Deckhand's initialization script to search for config files.
    export DECKHAND_CONFIG_DIR=$CONF_DIR

    cp etc/deckhand/logging.conf.sample $CONF_DIR/logging.conf

# Create a logging config file to dump everything to stdout/stderr.
cat <<EOCONF > $CONF_DIR/logging.conf
[loggers]
keys = root, deckhand, error

[handlers]
keys = null, stderr, stdout

[formatters]
keys = simple, context

[logger_deckhand]
level = DEBUG
handlers = stdout
qualname = deckhand

[logger_error]
level = ERROR
handlers = stderr

[logger_root]
level = WARNING
handlers = null

[handler_stderr]
class = StreamHandler
args = (sys.stderr,)
formatter = context

[handler_stdout]
class = StreamHandler
args = (sys.stdout,)
formatter = context

[handler_null]
class = logging.NullHandler
formatter = context
args = ()

[formatter_context]
class = oslo_log.formatters.ContextFormatter

[formatter_simple]
format=%(asctime)s.%(msecs)03d %(process)d %(levelname)s: %(message)s
EOCONF

# Create a Deckhand config file with bare minimum options.
cat <<EOCONF > $CONF_DIR/deckhand.conf
[DEFAULT]
debug = true
publish_errors = true
use_stderr = true

function deploy_deckhand {
    gen_config "http://localhost:9000"
    gen_paste true
    gen_policy

    if [ -z "$DECKHAND_IMAGE" ]; then
        log_section "Running Deckhand via uwsgi"

        alembic upgrade head
        # NOTE(fmontei): Deckhand's database is not configured to work with
        # multiprocessing. Currently there is a data race on acquiring shared
        # SQLAlchemy engine pooled connection strings when workers > 1. As a
        # workaround, we use multiple threads but only 1 worker. For more
        # information, see: https://github.com/att-comdev/deckhand/issues/20
        export DECKHAND_API_WORKERS=1
        export DECKHAND_API_THREADS=4
        source $ROOTDIR/../entrypoint.sh server &
    else
        log_section "Running Deckhand via Docker"
        sudo docker run \
            --rm \
            --net=host \
            -v $CONF_DIR:/etc/deckhand \
            $DECKHAND_IMAGE alembic upgrade head &> $STDOUT &
        sudo docker run \
            --rm \
            --net=host \
            -p 9000:9000 \
            -v $CONF_DIR:/etc/deckhand \
            $DECKHAND_IMAGE server &> $STDOUT &
    fi
[oslo_policy]
policy_file = policy.yaml

[barbican]

[database]
connection = $DATABASE_URL

[keystone_authtoken]
# Populate keystone_authtoken with values like the following should Keystone
# integration be needed here.
# project_domain_name = Default
# project_name = admin
# user_domain_name = Default
# password = devstack
# username = admin
# auth_url = http://127.0.0.1/identity
# auth_type = password
EOCONF

    echo $CONF_DIR/deckhand.conf 1>&2
    cat $CONF_DIR/deckhand.conf 1>&2

    echo $CONF_DIR/logging.conf 1>&2
    cat $CONF_DIR/logging.conf 1>&2

    # Only set up logging if running Deckhand via uwsgi. The container already has
    # values for logging.
    if $RUN_WITH_UWSGI; then
        sed '1 a log_config_append = '"$CONF_DIR"'/logging.conf' $CONF_DIR/deckhand.conf
    fi
}

function use_noauth_paste {
    log_section Using noauth-paste.ini without [filter:authtoken]
    cp etc/deckhand/noauth-paste.ini $CONF_DIR/
}

function gen_policy {
    log_section Creating policy file with liberal permissions

    policy_file='etc/deckhand/policy.yaml.sample'
    policy_pattern="deckhand\:"

    touch $CONF_DIR/policy.yaml

    # Give the server a chance to come up. Better to poll a health check.
    sleep 5

    DECKHAND_ID=$(sudo docker ps | grep deckhand | awk '{print $1}')
    echo $DECKHAND_ID
}


# Deploy Deckhand and PostgreSQL and run tests.
deploy_postgre
deploy_deckhand


gen_config
use_noauth_paste
gen_policy

if $RUN_WITH_UWSGI; then
    log_section "Running Deckhand via uwsgi"

    # NOTE(fmontei): This will fail with any DB other than PostgreSQL.
    alembic upgrade head

    # NOTE(fmontei): Deckhand's database is not configured to work with
    # multiprocessing. Currently there is a data race on acquiring shared
    # SQLAlchemy engine pooled connection strings when workers > 1. As a
    # workaround, we use multiple threads but only 1 worker. For more
    # information, see: https://github.com/att-comdev/deckhand/issues/20
    export DECKHAND_API_WORKERS=1
    export DECKHAND_API_THREADS=4

    source $ROOTDIR/../entrypoint.sh server &
else
    log_section "Running Deckhand via Docker"

    # If container is already running, kill it.
    DECKHAND_ID=$(sudo docker ps --filter ancestor=$DECKHAND_IMAGE --format "{{.ID}}")
    if [ -n "$DECKHAND_ID" ]; then
        sudo docker stop $DECKHAND_ID
    fi

    DECKHAND_ALEMBIC_ID=$(
        sudo docker run \
            --rm \
            --net=host \
            -v $CONF_DIR:/etc/deckhand \
            $DECKHAND_IMAGE alembic upgrade head &> $STDOUT &
    )
    echo $DECKHAND_ALEMBIC_ID

    DECKHAND_ID=$(
        sudo docker run \
            --rm \
            --net=host \
            -p 9000:9000 \
            -v $CONF_DIR:/etc/deckhand \
            $DECKHAND_IMAGE server --development-mode &> $STDOUT &
    )
    echo $DECKHAND_ID
fi

# Give the server a chance to come up. Better to poll a health check.
sleep 5

log_section Running tests

# Create folder for saving HTML test results.
mkdir -p $ROOTDIR/results

set +e
posargs=$@
if [ ${#posargs} -ge 1 ]; then
    py.test -k $1 -svx $( dirname $ROOTDIR )/deckhand/tests/functional/test_gabbi.py --html=results/index.html
else
    py.test -svx $( dirname $ROOTDIR )/deckhand/tests/functional/test_gabbi.py --html=results/index.html
fi
TEST_STATUS=$?
set -e

if [ "x$TEST_STATUS" = "x0" ]; then
    log_section Done SUCCESS
else
    log_section Deckhand Server Log
    cat $STDOUT
    log_section Done FAILURE
    exit $TEST_STATUS
fi
