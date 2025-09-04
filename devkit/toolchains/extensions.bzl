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

load(":rules.bzl", "local_archive")

def _local_sysroot_impl(ctx):
    for module in ctx.modules:
        sysroot_tags = getattr(module.tags, "sysroot", None)
        if sysroot_tags:
            for tag_data in sysroot_tags:
                local_archive(
                    name = "sysroot",
                    sha256 = tag_data.sha256,
                    config = tag_data.config,
                )

local_sysroot = module_extension(
    implementation = _local_sysroot_impl,
    tag_classes = {
        "sysroot": tag_class(attrs = {
            "config": attr.label(
                mandatory = True,
                doc = "Path to the devkit.json file.",
                allow_single_file = True,
            ),
            "sha256": attr.string(
                mandatory = True,
                doc = "Expected SHA256 hash of the generated archive.",
            ),
        }),
    },
)
