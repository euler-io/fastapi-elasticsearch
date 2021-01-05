#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [ ! -d "$SCRIPT_DIR/docker-compose/dev-certificates" ]; then
	OUTPUT=$SCRIPT_DIR/docker-compose/dev-certificates $SCRIPT_DIR/docker-compose/generate_certificates.sh
fi

CURRENT_UID=$(id -u) CURRENT_GID=$(id -g) docker-compose -f $SCRIPT_DIR/docker-compose-dev.yml up