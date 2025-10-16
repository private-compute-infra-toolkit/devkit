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

set -o errexit
set -o nounset
set -o xtrace

export TZ=Etc/UTC
export PS4='+\t $(basename ${BASH_SOURCE[0]}):${LINENO} '

trap popd EXIT
pushd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null

EXPECTED="$(pwd)"
readonly EXPECTED

# The devkit command is designed to be run from any subdirectory
# of the project. It should correctly identify the project root.
# The `build` command executes the given command inside the
# development container, in the current working directory.
ACTUAL="$(../../../devkit/build pwd)"
readonly ACTUAL

if [[ "${ACTUAL}" != "${EXPECTED}" ]]; then
  printf "Execution in subdirectory test failed!\n" >/dev/stderr
  printf "  expected: %s\n" "${EXPECTED}" >/dev/stderr
  printf "  actual:   %s\n" "${ACTUAL}" >/dev/stderr
  exit 1
fi
