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

# docker:28.2.2 last pushed on Jun 13, 2025 at 10:07 am
ARG DOCKER_DIGEST=sha256:ff052514f359111edd920b54581e7aca65629458607f9fbdbf82d7eefbe0602b

# docker/buildx-bin:v0.25 last pushed on Jun 12, 2025 at 1:00 am
ARG DOCKER_BUILDX_DIGEST=sha256:ca0b674e823a702b3af483197ed61b8028ef17bd1b59ecb9471945ca69efb993

FROM docker@${DOCKER_DIGEST} AS docker-image

FROM docker/buildx-bin@${DOCKER_BUILDX_DIGEST} AS docker-buildx-image

FROM ubuntu:24.04

COPY --from=docker-image /usr/local/bin/docker /usr/local/bin/docker
ENV PATH="/usr/local/bin:${PATH}"

COPY --from=docker-buildx-image /buildx /usr/libexec/docker/cli-plugins/docker-buildx

ARG SUDO_VERSION=1.9.15p5-*
ARG GIT_VERSION=1:2.43.0-*
ARG PYTHON3_MINIMAL_VERSION=3.12.3-*
ARG PYTHON3_JINJA2_VERSION=3.1.2-*

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    sudo=${SUDO_VERSION} \
    git=${GIT_VERSION} \
    python3-minimal=${PYTHON3_MINIMAL_VERSION} \
    python3-jinja2=${PYTHON3_JINJA2_VERSION} \
 && rm -rf /var/lib/apt/lists/*
