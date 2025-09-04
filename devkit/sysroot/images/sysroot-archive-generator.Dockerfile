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

RUN mkdir -p /sysroot/usr

RUN cp -R /usr/include /sysroot/usr/include \
  && cp -R /usr/lib /sysroot/usr/lib \
  && cp -R /lib /sysroot/lib \
  && mkdir -p /sysroot/lib64 \
  && cp -R --dereference /lib64/* /sysroot/lib64

RUN tar \
  --sort=name \
  --mtime='1970-01-01 00:00:00Z' \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  --create \
  --gzip \
  --file=/sysroot.tar.gz \
  --directory=/sysroot \
  .
