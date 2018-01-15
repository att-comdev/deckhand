#!/usr/bin/env bash

function cleanup {
    pifpaf_stop
}

trap cleanup EXIT

set -ex
eval `pifpaf run postgresql`
env | grep PIFPAF
set +ex

set -eo pipefail

TESTRARGS=$1

# --until-failure is not compatible with --subunit see:
#
# https://bugs.launchpad.net/testrepository/+bug/1411804
#
# this work around exists until that is addressed
if [[ "$TESTARGS" =~ "until-failure" ]]; then
    python setup.py testr --slowest --testr-args="--concurrency=1 $TESTRARGS"
else
    python setup.py testr --slowest --testr-args="--subunit --concurrency=1 $TESTRARGS" | subunit-trace -f
fi
