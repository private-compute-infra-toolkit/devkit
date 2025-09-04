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

# ubuntu:22.04 last pushed on Jun 3, 2025 at 7:04 am
ARG UBUNTU_DIGEST=sha256:01a3ee0b5e413cefaaffc6abe68c9c37879ae3cced56a8e088b1649e5b269eee

FROM ubuntu@${UBUNTU_DIGEST}

ARG LINUX_LIBC_DEV=5.15.0-156.166
ARG LIBC_DEV_VERSION=2.35-0ubuntu3.10
ARG LIBCRYPT_DEV_VERSION=4.4.27-1
ARG LIBTIRPC_DEV_VERSION=1.3.2-2ubuntu0.1
ARG LIBSNL_DEV_VERSION=1.3.0-2build2
ARG RPCSVC_PROTO_VERSION=1.4.2-0ubuntu6
ARG LIBC6_DEV_VERSION=2.35-0ubuntu3.10

ARG SECURITY=http://security.ubuntu.com/ubuntu/pool/main
ARG ARCHIVE=http://archive.ubuntu.com/ubuntu/pool/main

ADD ${SECURITY}/l/linux/linux-libc-dev_${LINUX_LIBC_DEV}_amd64.deb linux-libc-dev.deb
RUN dpkg -i linux-libc-dev.deb

ADD ${ARCHIVE}/g/glibc/libc-dev-bin_${LIBC_DEV_VERSION}_amd64.deb libc-dev-bin.deb
RUN dpkg -i libc-dev-bin.deb

ADD ${ARCHIVE}/libx/libxcrypt/libcrypt-dev_${LIBCRYPT_DEV_VERSION}_amd64.deb libcrypt-dev.deb
RUN dpkg -i libcrypt-dev.deb

ADD ${ARCHIVE}/libt/libtirpc/libtirpc-dev_${LIBTIRPC_DEV_VERSION}_amd64.deb libtirpc-dev.deb
RUN dpkg -i libtirpc-dev.deb

ADD ${SECURITY}/libn/libnsl/libnsl-dev_${LIBSNL_DEV_VERSION}_amd64.deb libnsl-dev.deb
RUN dpkg -i libnsl-dev.deb

ADD ${ARCHIVE}/r/rpcsvc-proto/rpcsvc-proto_${RPCSVC_PROTO_VERSION}_amd64.deb rpcsvc-proto.deb
RUN dpkg -i rpcsvc-proto.deb

ADD ${ARCHIVE}/g/glibc/libc6-dev_${LIBC6_DEV_VERSION}_amd64.deb libc6-dev.deb
RUN dpkg -i libc6-dev.deb

RUN ln -s /lib/x86_64-linux-gnu/libgcc_s.so.1 /lib/libgcc_s.so.1 \
 && ln -s /lib/libgcc_s.so.1 /lib/libgcc_s.so
