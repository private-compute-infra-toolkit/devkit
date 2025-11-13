#!/bin/bash
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

set -o errexit
set -o nounset

sudo rm -rf /usr/local/lib/android
sudo rm -rf /usr/share/dotnet
sudo rm -rf /opt/ghc
sudo rm -rf /usr/local/.ghcup
sudo rm -rf /opt/codeql
sudo rm -rf /usr/share/swift
sudo docker system prune -a -f
