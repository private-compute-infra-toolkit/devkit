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
export PS4='+	 $(basename ${BASH_SOURCE[0]}):${LINENO} '

function cleanup() {
  if [[ -f devkit.json.bak ]]; then
    mv devkit.json.bak devkit.json
  fi
}
trap cleanup EXIT

if [[ -f devkit.json ]]; then
  cp devkit.json devkit.json.bak
fi

python3 - <<'EOF'
import json
import os

devkit_json_path = "devkit.json"

if os.path.exists(devkit_json_path):
    with open(devkit_json_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
else:
    data = {}

if "docker" not in data:
    data["docker"] = {}

data["docker"]["run"] = ["--env=KEY=VALUE"]

with open(devkit_json_path, "w") as f:
    json.dump(data, f, indent=2)
EOF

# To disable warning about single variable expansion in `bash -c '...'`.
# We do not want to expand before the call, but in the container.
# shellcheck disable=SC2016
OUTPUT="$(devkit/build bash -c 'echo -n $KEY')"

if [[ "${OUTPUT}" != "VALUE" ]]; then
  echo "devkit.json docker run args test failed!"
  echo "Expected: VALUE"
  echo "Got: ${OUTPUT}"
  exit 1
fi
