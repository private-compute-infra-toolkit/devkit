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
export GIT_ALLOW_PROTOCOL=file
export PS4='+	 $(basename ${BASH_SOURCE[0]}):${LINENO} '

MOCK_DIR="$(mktemp -d)"
readonly MOCK_DIR

function cleanup() {
  if [[ -d "${MOCK_DIR}" ]]; then
    popd > /dev/null 2>&1 || true
    rm -rf "${MOCK_DIR}"
  fi
}
trap cleanup EXIT

readonly GITLINKS_CMD="${PWD}/devkit/gitlinks"

# Create a "remote" repo to be used as a submodule
REMOTE_REPO_1="${MOCK_DIR}/remote1"
mkdir -p "${REMOTE_REPO_1}"
pushd "${REMOTE_REPO_1}"
git init -b main
echo "initial 1" > file1.txt
git add file1.txt
git commit -m "initial commit 1"
popd

REMOTE_REPO_2="${MOCK_DIR}/remote2"
mkdir -p "${REMOTE_REPO_2}"
pushd "${REMOTE_REPO_2}"
git init -b main
echo "initial 2" > file2.txt
git add file2.txt
git commit -m "initial commit 2"
popd

# Create the main test repo
MAIN_REPO="${MOCK_DIR}/main"
mkdir -p "${MAIN_REPO}"
pushd "${MAIN_REPO}"
git init -b main

# --- Test Group 1: --check ---
echo "Testing --check..."

# Test case 1.1: No submodules
"${GITLINKS_CMD}" --check

# Test case 1.2: Multiple submodules in sync
git submodule add "${REMOTE_REPO_1}" sub1
git submodule add "${REMOTE_REPO_2}" sub2
git commit -m "add submodules"
"${GITLINKS_CMD}" --check

# Test case 1.3: Submodule out of sync (index != disk)
pushd sub1
git commit --allow-empty -m "new commit on disk"
popd

# Now it is out of sync
OUTPUT=$( "${GITLINKS_CMD}" --check 2>&1 || true )
EXPECTED="Error: Submodules are out of sync with gitlinks."
if [[ ! "${OUTPUT}" =~ ${EXPECTED} ]]; then
  echo "Test Case 1.3 Failed: Expected error message to contain: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

git submodule update --init --recursive
"${GITLINKS_CMD}" --check

# Test case 1.4: Submodule SHA mismatch with remote branch (index == disk != remote)
pushd "${REMOTE_REPO_2}"
git commit --allow-empty -m "update remote 2"
popd

# target_sha (remote) will be newer than current_sha (index)
OUTPUT=$( "${GITLINKS_CMD}" --check 2>&1 || true )
EXPECTED="Error: Submodule 'sub2' gitlink (.*) does not match remote branch 'main' (.*)."
if [[ ! "${OUTPUT}" =~ ${EXPECTED} ]]; then
  echo "Test Case 1.4 Failed: Expected error message to match pattern: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

# --- Test Group 2: --update ---
echo "Testing --update..."

# Test case 2.1: Update all submodules
"${GITLINKS_CMD}" --update
# After update, both should be in sync and staged
"${GITLINKS_CMD}" --check
if [[ -z "$(git status --porcelain sub1 sub2)" ]]; then
  echo "Test Case 2.1 Failed: Expected submodules to be staged after update."
  exit 1
fi
git commit -m "sync submodules"

# --- Test Group 3: --install ---
echo "Testing --install..."

# Test case 3.1: No .pre-commit-config.yaml
OUTPUT=$( "${GITLINKS_CMD}" --install 2>&1 || true )
EXPECTED="Error: .pre-commit-config.yaml not found in current directory."
if [[ ! "${OUTPUT}" =~ ${EXPECTED} ]]; then
  echo "Test Case 3.1 Failed: Expected error message to contain: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

# Test case 3.2: Create new section
echo "repos:" > .pre-commit-config.yaml
"${GITLINKS_CMD}" --install
grep -q "id: gitlinks" .pre-commit-config.yaml
grep -q "entry: devkit/gitlinks --check" .pre-commit-config.yaml

# Test case 3.3: Idempotency
BEFORE_MD5=$(md5sum .pre-commit-config.yaml | awk '{print $1}')
"${GITLINKS_CMD}" --install
AFTER_MD5=$(md5sum .pre-commit-config.yaml | awk '{print $1}')
if [[ "${BEFORE_MD5}" != "${AFTER_MD5}" ]]; then
  echo "Test Case 3.3 Failed: --install is not idempotent."
  exit 1
fi

# Test case 3.4: Existing repo: local section
cat <<EOF > .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: other
        entry: true
EOF
"${GITLINKS_CMD}" --install
# Check if it was inserted into the existing section
grep -A 5 "repo: local" .pre-commit-config.yaml | grep -q "id: gitlinks"

echo "All devkit/gitlinks tests passed."
popd
