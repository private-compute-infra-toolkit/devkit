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

ARG BASE

# hadolint ignore=DL3006
FROM ${BASE}

ARG CODE_VERSION=1.103.0-*

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

RUN apt-get update \
 && wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg \
 && install -D packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg \
 && echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | tee /etc/apt/sources.list.d/vscode.list > /dev/null \
 && rm -f packages.microsoft.gpg \
 && apt-get update && apt-get install -y --no-install-recommends code=${CODE_VERSION} \
 && rm -rf /var/lib/apt/lists/*

ARG EXTRA_PACKAGES=""
RUN if [ -n "${EXTRA_PACKAGES}" ]; then \
    apt-get update \
    && apt-get install -y --no-install-recommends ${EXTRA_PACKAGES} \
    && rm -rf /var/lib/apt/lists/*; \
    fi
