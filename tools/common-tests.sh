#!/usr/bin/env bash

function log_section {
    set +x
    echo 1>&2
    echo 1>&2
    echo === $* === 1>&2
    set -x
}


function deploy_postgre {
    set -xe

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
}


function gen_config {
    #######################################
    # Generate sample configuration file
    # Globals:
    #   CONF_DIR
    #   DECKHAND_TEST_URL
    #   DATABASE_URL
    #   DECKHAND_CONFIG_DIR
    # Arguments:
    #   disable_keystone: true or false
    #   Deckhand test URL: URL to Deckhand wsgi server
    # Returns:
    #   None
    #######################################
    set -xe

    log_section "Creating config directory and test deckhand.conf"

    local disable_keystone=$1

    CONF_DIR=$(mktemp -d -p $(pwd))
    sudo chmod 777 -R $CONF_DIR

    export DECKHAND_TEST_URL=$2
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
development_mode = false

[oslo_policy]
policy_file = policy.yaml

[barbican]

[database]
connection = $DATABASE_URL

[keystone_authtoken]
# NOTE(fmontei): Values taken from clouds.yaml. Values only used for
# integration testing.
#
# clouds.yaml (snippet):
#
# username: 'admin'
# password: 'password'
# project_name: 'admin'
# project_domain_name: 'default'
# user_domain_name: 'default'
# auth_url: 'http://keystone.openstack.svc.cluster.local/v3'

username = admin
password = password
project_name = admin
project_domain_name = Default
user_domain_name = Default
auth_url = http://keystone.openstack.svc.cluster.local/v3
auth_type = password
EOCONF

    # Only set up logging if running Deckhand via uwsgi. The container already has
    # values for logging.
    if [ -z "$DECKHAND_IMAGE" ]; then
        sed '1 a log_config_append = '"$CONF_DIR"'/logging.conf' $CONF_DIR/deckhand.conf
    fi

    if $disable_keystone; then
        log_section "Toggling development_mode on to disable Keystone authentication."
        sed -i -e 's/development_mode = false/development_mode = true/g' $CONF_DIR/deckhand.conf
    fi

    echo $CONF_DIR/deckhand.conf 1>&2
    cat $CONF_DIR/deckhand.conf 1>&2

    echo $CONF_DIR/logging.conf 1>&2
    cat $CONF_DIR/logging.conf 1>&2
}


function gen_paste {
    #######################################
    # Generate sample paste.ini file
    # Globals:
    #   CONF_DIR
    # Arguments:
    #   disable_keystone: true or false
    # Returns:
    #   None
    #######################################
    set -xe

    local disable_keystone=$1

    if $disable_keystone; then
        log_section "Using noauth-paste.ini to disable Keystone authentication."
        cp etc/deckhand/noauth-paste.ini $CONF_DIR/noauth-paste.ini
    else
        cp etc/deckhand/deckhand-paste.ini $CONF_DIR/deckhand-paste.ini
    fi
}


function gen_policy {
    set -xe

    log_section "Creating policy file with liberal permissions."

    local policy_file='etc/deckhand/policy.yaml.sample'
    local policy_pattern="deckhand\:"

    touch $CONF_DIR/policy.yaml

    sed -n "/$policy_pattern/p" "$policy_file" \
        | sed 's/^../\"/' \
        | sed 's/rule\:[A-Za-z\_\-]*/@/' > $CONF_DIR/policy.yaml

    echo $CONF_DIR/'policy.yaml' 1>&2
    cat $CONF_DIR/'policy.yaml' 1>&2
}
