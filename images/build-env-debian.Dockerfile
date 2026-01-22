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

ARG GOLANG_IMAGE=golang:1.24.5-bookworm
ARG DEBIAN_IMAGE=debian:bookworm-slim

FROM docker@${DOCKER_DIGEST} AS docker-image

FROM docker/buildx-bin@${DOCKER_BUILDX_DIGEST} AS docker-buildx-image

FROM ${GOLANG_IMAGE} AS golang-image

FROM ${DEBIAN_IMAGE}

ARG BAZELISK_VERSION=v1.27.0
ARG LIBXML2_VERSION=2.*
ARG CURL_VERSION=*
ARG GNUPG_VERSION=*

COPY --from=docker-image /usr/local/bin/docker /usr/local/bin/docker
ENV PATH="/usr/local/bin:${PATH}"

COPY --from=docker-buildx-image /buildx /usr/libexec/docker/cli-plugins/docker-buildx

COPY --from=golang-image /usr/local/go/ /usr/local/go/
ENV PATH="/usr/local/go/bin:${PATH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
 ca-certificates \
 curl=${CURL_VERSION} \
 git \
 gnupg=${GNUPG_VERSION} \
 libxml2=${LIBXML2_VERSION} \
 python3 \
 sudo \
 && rm -rf /var/lib/apt/lists/*

ARG GOBIN=/usr/local/bin
RUN GOBIN="${GOBIN}" go install github.com/bazelbuild/bazelisk@${BAZELISK_VERSION} \
 && ln -sf "${GOBIN}"/bazelisk "${GOBIN}"/bazel

ARG EXTRA_KEYS=""
RUN for key_entry in ${EXTRA_KEYS}; do \
       key_name=$(echo "$key_entry" | cut -d'=' -f1); \
       key_url=$(echo "$key_entry" | cut -d'=' -f2-); \
       curl -fsSL "${key_url}" | gpg --dearmor -o "/usr/share/keyrings/${key_name}.gpg"; \
    done

ARG EXTRA_REPOSITORIES=""
RUN for repo_entry in ${EXTRA_REPOSITORIES}; do \
      repo_name=$(echo "$repo_entry" | cut -d'=' -f1); \
      repo_url=$(echo "$repo_entry" | cut -d'=' -f2-); \
      echo "deb [signed-by=/usr/share/keyrings/${repo_name}.gpg] ${repo_url} bookworm main" > "/etc/apt/sources.list.d/${repo_name}.list"; \
    done

ARG EXTRA_PACKAGES=""
RUN if [ -n "${EXTRA_PACKAGES}" ]; then \
    apt-get update \
    && apt-get install -y --no-install-recommends ${EXTRA_PACKAGES} \
    && rm -rf /var/lib/apt/lists/*; \
    fi
