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

ARG GOLAND_VERSION=2025.2.1

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

RUN wget -O- https://download.jetbrains.com/go/goland-${GOLAND_VERSION}.tar.gz | tar -xz \
 && mv GoLand-${GOLAND_VERSION}/ /opt/goland

RUN echo "-Dremote.x11.workaround=true" >> /opt/goland/bin/goland64.vmoptions
