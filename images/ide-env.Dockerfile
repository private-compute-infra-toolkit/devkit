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

ARG FREETYPE_VERSION=2.13.2+dfsg-*
ARG XEXT_VERSION=2:1.3.4-*
ARG XRENDER_VERSION=1:0.9.10-*
ARG XTST_VERSION=2:1.2.3-*
ARG XI_VERSION=2:1.8.1-*
ARG FONTCONFIG_VERSION=2.15.0-*
ARG X11_UTILS_VERSION=7.7+*
ARG XAUTH_VERSION=1:1.1.2-*
ARG GPG_VERSION=2.4.4-*
ARG GOOGLE_CHROME_STABLE_VERSION=*

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libfreetype6=${FREETYPE_VERSION} \
    libxext6=${XEXT_VERSION} \
    libxrender1=${XRENDER_VERSION} \
    libxtst6=${XTST_VERSION} \
    libxi6=${XI_VERSION} \
    libfontconfig1=${FONTCONFIG_VERSION} \
    x11-utils=${X11_UTILS_VERSION} \
    xauth=${XAUTH_VERSION} \
    gpg=${GPG_VERSION} \
 && rm -rf /var/lib/apt/lists/*

 RUN apt-get update \
  && mkdir -p /etc/apt/keyrings \
  && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
  && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
     google-chrome-stable=${GOOGLE_CHROME_STABLE_VERSION} \
  && rm -rf /var/lib/apt/lists/* \
  && rm -f /etc/apt/sources.list.d/google-chrome.list /etc/apt/keyrings/google-chrome.gpg

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
