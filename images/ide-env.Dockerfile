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
 && rm -rf /var/lib/apt/lists/*
