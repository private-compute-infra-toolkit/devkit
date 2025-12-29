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
  if [[ -d "${TEST_DIR:-}" ]]; then
    rm -rf "${TEST_DIR}"
  fi
}
trap cleanup EXIT

# Backup devkit.json
if [[ -f devkit.json ]]; then
  cp devkit.json devkit.json.bak
fi

# Modify devkit.json to switch to other registry
# We will use python to modify the json safely
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
if "registry" not in data["docker"]:
    data["docker"]["registry"] = {}

# Use a test registry
data["docker"]["registry"]["host"] = "test-host"
data["docker"]["registry"]["repository"] = "test-repo"
data["docker"]["registry"]["project"] = "test-project"

with open(devkit_json_path, "w") as f:
    json.dump(data, f, indent=2)
EOF

TEST_DIR="$(mktemp -d)"
readonly TEST_DIR
readonly IMAGE_NAME="tool-env"

# 2. Check whether devkit/tool works in that new setup
# This ensures the image is built with the new tag derived from the new registry config.
# We execute 'true' to just check if it runs.
devkit/tool true

# Get the tag that was built/used
TAG="$(python3 scripts/docker/build.py "${IMAGE_NAME}" --print-tag --search-path images --config devkit.json)"
readonly TAG
echo "Built image tag: ${TAG}"

# Verify tag prefix
readonly EXPECTED_PREFIX="test-host/test-project/test-repo/devkit/${IMAGE_NAME}:amd64-"
if [[ "${TAG}" != "${EXPECTED_PREFIX}"* ]]; then
  echo "Error: Tag ${TAG} does not start with expected prefix ${EXPECTED_PREFIX}"
  exit 1
fi

# 3. Do the vendoring
devkit/vendor --dir "${TEST_DIR}" --config devkit.json "${IMAGE_NAME}"

# 4. Check the output directory
readonly EXPECTED_FILE="${TEST_DIR}/${TAG}.tar"
if [[ ! -f "${EXPECTED_FILE}" ]]; then
  echo "Error: Vendored file ${EXPECTED_FILE} not found."
  exit 1
fi

# 5. Remove the image from docker
docker rmi "${TAG}"

# Verify it's gone
if docker image inspect "${TAG}" >/dev/null 2>&1; then
   echo "Error: Image ${TAG} was not removed."
   exit 1
fi

# 6. Load back the image
devkit/vendor --dir "${TEST_DIR}" --load

# Verify it's back
if ! docker image inspect "${TAG}" >/dev/null 2>&1; then
   echo "Error: Image ${TAG} was not loaded back."
   exit 1
fi

# 7. Recheck whether the command works
devkit/tool true

echo "devkit/vendor integration test passed."
