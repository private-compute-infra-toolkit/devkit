#!/bin/bash
# Copyright 2025 Google LLC
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

# This script is meant to be sourced by other scripts to enable xtrace logging.
#
# Usage:
#   source lib_logging.sh

# require this script to be sourced rather than executed
if ! (return 0 2>/dev/null); then
  printf "Error: Script %s must be sourced\n" "${BASH_SOURCE[0]}" &>/dev/stderr
  exit 1
fi

SCRIPT_NAME=$(basename "$0")
readonly SCRIPT_NAME

readonly DEVKIT_LOGS_DIR="${HOME}/.devkit/logs"
mkdir -p "${DEVKIT_LOGS_DIR}"

TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S.%N')
readonly TIMESTAMP

export DEVKIT_LOG_FILE="${DEVKIT_LOGS_DIR}/${TIMESTAMP}-${SCRIPT_NAME}.log"
readonly DEVKIT_LOG_FILE

export TZ=Etc/UTC
export PS4='+\t $(basename ${BASH_SOURCE[0]}):${LINENO} ' # xtrace prompt

# Redirect xtrace to the log file, leaving stdout/stderr untouched.
# BASH_XTRACEFD is a bash-specific variable that controls where xtrace logs are sent.
exec {BASH_XTRACEFD}>"${DEVKIT_LOG_FILE}"

set -o xtrace
