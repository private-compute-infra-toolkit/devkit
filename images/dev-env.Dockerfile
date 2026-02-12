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

ARG WGET_VERSION=1.21.4-*
ARG PRE_COMMIT_VERSION=3.6.2-*
ARG NEOVIM_VERSION=0.9.5-*
ARG NVM_VERSION=v0.40.3
ARG NODE_VERSION=v22.21.1
ARG FDFIND_VERSION=9.0.0-*
ARG RIPGREP_VERSION=14.1.0-*
ARG GEMINI_CLI_VERSION=0.28.2
ARG COMMIT_AND_TAG_VERSION_VERSION=10.1.0
ARG SHELLCHECK_VERSION=0.9.0-*
ARG GITLINT_VERSION=0.19.1-*

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

RUN apt-get update \
   && apt-get install -y --no-install-recommends \
   fd-find=${FDFIND_VERSION} \
   gitlint=${GITLINT_VERSION} \
   neovim=${NEOVIM_VERSION} \
   pre-commit=${PRE_COMMIT_VERSION} \
   ripgrep=${RIPGREP_VERSION} \
   shellcheck=${SHELLCHECK_VERSION} \
   wget=${WGET_VERSION} \
   && rm -rf /var/lib/apt/lists/*

ARG NVM_DIR=/usr/local/nvm
ADD https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh /tmp/nvm_install.sh
RUN mkdir -p "${NVM_DIR}" \
  && chmod 500 /tmp/nvm_install.sh \
  && /tmp/nvm_install.sh \
  && source "${NVM_DIR}/nvm.sh" \
  && nvm install "${NODE_VERSION}" \
  && nvm use --delete-prefix "${NODE_VERSION}"
ENV NODE_PATH="${NVM_DIR}/versions/node/${NODE_VERSION}/lib/node_modules"
ARG NODE_BIN="${NVM_DIR}/versions/node/${NODE_VERSION}/bin"
ENV PATH="${NODE_BIN}:${PATH}"
RUN npm install -g \
    @google/gemini-cli@${GEMINI_CLI_VERSION} \
    commit-and-tag-version@${COMMIT_AND_TAG_VERSION_VERSION} \
   && ln -s "${NODE_BIN}/gemini" /bin/gemini \
   && ln -s "${NODE_BIN}/commit-and-tag-version" /bin/commit-and-tag-version

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
