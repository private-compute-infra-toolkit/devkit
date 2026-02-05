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

MOCK_DIR="$(mktemp -d)"
readonly MOCK_DIR

function cleanup() {
  if [[ -d "${MOCK_DIR}" ]]; then
    popd > /dev/null 2>&1 || true
    rm -rf "${MOCK_DIR}"
  fi
}
trap cleanup EXIT

readonly DEVKIT_CHECK_CHECKSUMS="${PWD}/devkit/check_checksums"

# Function to remove ANSI color codes
strip_colors() {
  sed 's/\x1b\[[0-9;]*m//g'
}

pushd "${MOCK_DIR}" > /dev/null

# Test case 1: No checksums.txt file
OUTPUT=$( "${DEVKIT_CHECK_CHECKSUMS}" 2>&1 | strip_colors || true )
EXPECTED="Error: checksums.txt not found."
if [[ "${OUTPUT}" != "${EXPECTED}" ]]; then
  echo "Test Case 1 Failed: Expected output: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

# Test case 2: Empty checksums.txt file
touch "checksums.txt"
OUTPUT=$( "${DEVKIT_CHECK_CHECKSUMS}" 2>&1 | strip_colors )
EXPECTED="No files to verify. The checksums.txt is empty or only contains whitespace."
if [[ "${OUTPUT}" != "${EXPECTED}" ]]; then
  echo "Test Case 2 Failed: Expected output: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

# Test case 3: Matching checksums
echo "Hello World" > "test1.txt"
CHECKSUM=$(sha256sum "test1.txt" | awk '{print $1}')
echo "${CHECKSUM}  test1.txt" > "checksums.txt"
OUTPUT=$( "${DEVKIT_CHECK_CHECKSUMS}" 2>&1 | strip_colors )
EXPECTED="Verifying checksum for test1.txt ... OK
All checksums verified successfully."
if [[ "${OUTPUT}" != "${EXPECTED}" ]]; then
  echo "Test Case 3 Failed: Expected output: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

# Test case 4: Non-matching checksums
EXPECTED_CHECKSUM="d2a84f4b8b650937ec8f73cd8be2c74add5a911ba64df27458ed8229da804a26"
echo "${EXPECTED_CHECKSUM}  test1.txt" > "checksums.txt"
echo "Different Content" > "test1.txt"
ACTUAL_CHECKSUM=$(sha256sum "test1.txt" | awk '{print $1}')
OUTPUT=$( "${DEVKIT_CHECK_CHECKSUMS}" 2>&1 | strip_colors || true )
EXPECTED="Verifying checksum for test1.txt ... FAILED
  Expected: ${EXPECTED_CHECKSUM}
  Actual:   ${ACTUAL_CHECKSUM}
Checksums verification failed."
if [[ "${OUTPUT}" != "${EXPECTED}" ]]; then
  echo "Test Case 4 Failed: Expected output: ${EXPECTED}"
  echo "Actual output: ${OUTPUT}"
  exit 1
fi

echo "All devkit/check_checksums tests passed."
