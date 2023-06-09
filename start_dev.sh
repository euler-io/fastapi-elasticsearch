#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


CURRENT_UID=$(id -u) CURRENT_GID=$(id -g) docker-compose -f $SCRIPT_DIR/docker-compose-dev.yml up