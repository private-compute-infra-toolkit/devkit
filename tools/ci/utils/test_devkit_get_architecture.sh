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

ACTUAL="$(devkit/get-architecture)"
readonly ACTUAL

if [[ ${ACTUAL} != amd64 ]] && [[ ${ACTUAL} != arm64 ]]; then
  printf "devkit/get-architecture test failed!\n" >/dev/stderr
  exit 1
fi
