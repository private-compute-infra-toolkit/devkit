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

ARG GCLOUD_CLI_VERSION=540.0.0

FROM gcr.io/google.com/cloudsdktool/google-cloud-cli:${GCLOUD_CLI_VERSION}-slim

ARG JQ_VERSION=1.6-*
ARG SUDO_VERSION=1.9.*

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    jq=${JQ_VERSION} \
    sudo=${SUDO_VERSION} \
 && rm -rf /var/lib/apt/lists/*

ARG EXTRA_PACKAGES=""
RUN if [ -n "${EXTRA_PACKAGES}" ]; then \
    apt-get update \
    && apt-get install -y --no-install-recommends ${EXTRA_PACKAGES} \
    && rm -rf /var/lib/apt/lists/*; \
    fi
