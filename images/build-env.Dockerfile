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

ARG GOLANG_IMAGE=golang:1.24.5-bookworm

FROM ${GOLANG_IMAGE} AS golang-image

# hadolint ignore=DL3006
FROM ${BASE}

ARG LIBXML2_VERSION=2.9.14+dfsg-*
ARG UNZIP_VERSION=6.0-*
ARG GROFF_VERSION=1.23.0-*
ARG GCLOUD_VERSION=525.0.0
ARG AWS_CLI_VERSION=2.33.0
ARG BAZELISK_VERSION=v1.27.0
ARG BUILDIFIER_VERSION=v8.2.1
ARG GH_VERSION=2.45.0-*
ARG JQ_VERSION=1.7.1-*

COPY --from=golang-image /usr/local/go/ /usr/local/go/
ENV PATH="/usr/local/go/bin:${PATH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libxml2=${LIBXML2_VERSION} \
    unzip=${UNZIP_VERSION} \
    groff=${GROFF_VERSION} \
 && rm -rf /var/lib/apt/lists/*

ADD https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-${GCLOUD_VERSION}-linux-x86_64.tar.gz /tmp/gcloud.tar.gz
RUN tar -xf /tmp/gcloud.tar.gz \
 && ./google-cloud-sdk/install.sh --quiet --usage-reporting false --override-components docker-credential-gcr \
 && rm /tmp/gcloud.tar.gz
ENV PATH="/google-cloud-sdk/bin:${PATH}"

ADD https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWS_CLI_VERSION}.zip /tmp/awscliv2.zip
RUN unzip /tmp/awscliv2.zip \
 && aws/install \
 && rm -rf aws

RUN export GOBIN=/usr/local/bin \
 && go install github.com/bazelbuild/bazelisk@${BAZELISK_VERSION} \
 && ln -sf ${GOBIN}/bazelisk ${GOBIN}/bazel

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    gh=${GH_VERSION} \
    jq=${JQ_VERSION} \
 && rm -rf /var/lib/apt/lists/*;

ADD https://github.com/bazelbuild/buildtools/releases/download/${BUILDIFIER_VERSION}/buildifier-linux-amd64 /usr/bin/buildifier
RUN chmod +x /usr/bin/buildifier

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
