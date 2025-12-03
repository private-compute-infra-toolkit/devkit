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

ARG CLION_VERSION=2025.1.3

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

RUN wget -O- https://download.jetbrains.com/cpp/CLion-${CLION_VERSION}.tar.gz | tar -xz \
 && mv clion-${CLION_VERSION}/ /opt/clion

RUN echo "-Dremote.x11.workaround=true" >> /opt/clion/bin/clion64.vmoptions

ARG EXTRA_PACKAGES=""
RUN if [ -n "${EXTRA_PACKAGES}" ]; then \
    apt-get update \
    && apt-get install -y --no-install-recommends ${EXTRA_PACKAGES} \
    && rm -rf /var/lib/apt/lists/*; \
    fi
