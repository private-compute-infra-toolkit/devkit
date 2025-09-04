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

ARG CURL_VERSION=8.5.0-*
ARG CODE_SERVER_VERSION=4.101.2

# curl is required by the vscode installation script
RUN apt-get update \
   && apt-get install -y --no-install-recommends curl="${CURL_VERSION}" \
   && rm -rf /var/lib/apt/lists/*

RUN curl -fsL https://code-server.dev/install.sh \
  | /bin/sh /dev/stdin --version ${CODE_SERVER_VERSION}
