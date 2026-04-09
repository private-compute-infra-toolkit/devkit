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

# Global ARGs for shared dependencies across stages
ARG CA_CERTIFICATES_VERSION=*
ARG LIBCURL_VERSION=8.5.0-*
ARG LIBEXPAT_VERSION=2.6.1-*
ARG LIBPCRE2_VERSION=10.42-*
ARG ZLIB_VERSION=1:1.3.dfsg-*

FROM docker@${DOCKER_DIGEST} AS docker-image

FROM docker/buildx-bin@${DOCKER_BUILDX_DIGEST} AS docker-buildx-image

FROM ubuntu:24.04 AS git-builder

# Pull in global ARGs
ARG CA_CERTIFICATES_VERSION
ARG LIBCURL_VERSION
ARG LIBEXPAT_VERSION
ARG LIBPCRE2_VERSION
ARG ZLIB_VERSION

# Build-specific ARGs
ARG AUTOCONF_VERSION=2.71-*
ARG BUILD_ESSENTIAL_VERSION=12.10ubuntu*
ARG LIBSSL_DEV_VERSION=3.0.13-*
ARG WGET_VERSION=1.21.4-*

ENV GIT_VERSION=2.54.0-rc0

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf=${AUTOCONF_VERSION} \
    build-essential=${BUILD_ESSENTIAL_VERSION} \
    ca-certificates=${CA_CERTIFICATES_VERSION} \
    libcurl4-gnutls-dev=${LIBCURL_VERSION} \
    libexpat1-dev=${LIBEXPAT_VERSION} \
    libpcre2-dev=${LIBPCRE2_VERSION} \
    libssl-dev=${LIBSSL_DEV_VERSION} \
    wget=${WGET_VERSION} \
    zlib1g-dev=${ZLIB_VERSION} \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/src && cd /usr/src && \
    wget -q https://github.com/git/git/archive/refs/tags/v${GIT_VERSION}.tar.gz -O git.tar.gz && \
    tar -zxf git.tar.gz && cd git-${GIT_VERSION} && \
    make configure && \
    ./configure --prefix=/usr/local --with-libpcre2 && \
    make -j$(nproc) all NO_GETTEXT=1 NO_TCLTK=1 && \
    make install DESTDIR=/tmp/git-install NO_GETTEXT=1 NO_TCLTK=1

FROM ubuntu:24.04

COPY --from=docker-image /usr/local/bin/docker /usr/local/bin/docker
ENV PATH="/usr/local/bin:${PATH}"

COPY --from=docker-buildx-image /buildx /usr/libexec/docker/cli-plugins/docker-buildx

COPY --from=git-builder /tmp/git-install/usr/local /usr/local

# Pull in global ARGs
ARG CA_CERTIFICATES_VERSION
ARG LIBCURL_VERSION
ARG LIBEXPAT_VERSION
ARG LIBPCRE2_VERSION
ARG ZLIB_VERSION

# Final stage specific ARGs
ARG SUDO_VERSION=1.9.15p5-*
ARG CURL_VERSION=8.5.0-*
ARG GNUPG_VERSION=2.4.4-*

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates=${CA_CERTIFICATES_VERSION} \
    curl=${CURL_VERSION} \
    gnupg=${GNUPG_VERSION} \
    sudo=${SUDO_VERSION} \
    libcurl3t64-gnutls=${LIBCURL_VERSION} \
    libexpat1=${LIBEXPAT_VERSION} \
    libpcre2-8-0=${LIBPCRE2_VERSION} \
    zlib1g=${ZLIB_VERSION} \
 && rm -rf /var/lib/apt/lists/*

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
