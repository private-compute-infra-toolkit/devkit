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

def _local_archive_impl(ctx):
    # Register additional tool dependencies
    ctx.path(Label("//devkit/sysroot/images:base.Dockerfile"))
    ctx.path(Label("//devkit/sysroot/images:sysroot-archive-generator.Dockerfile"))

    build_script_path = ctx.path(Label("//devkit/docker:build.py"))
    config_path = ctx.path(ctx.attr.config)
    deps_json = ctx.path(Label("//devkit/sysroot/images:deps.json"))
    get_tag_args = [
        str(build_script_path),
        "sysroot-archive-generator",
        "--print-tag",
        "--config",
        str(config_path),
        "--search-path",
        str(deps_json.dirname),
    ]
    get_tag_result = ctx.execute(get_tag_args)

    if get_tag_result.return_code != 0:
        fail(("Failed to get base image tag using %s: \nSTDOUT:\n%sSTDERR:\n%s") % (
            " ".join(get_tag_args),
            get_tag_result.stdout,
            get_tag_result.stderr,
        ))

    sysroot_archive_generator_image_tag = get_tag_result.stdout.strip().splitlines()[-1]
    if not sysroot_archive_generator_image_tag:
        fail("Base image tag script (%s) returned an empty tag." % " ".join(get_tag_args))

    sysroot_archive_dockerfile = ctx.path(Label("//devkit/sysroot/images:sysroot-archive.Dockerfile"))

    script_args = [
        "docker",
        "buildx",
        "build",
        "--build-arg=BASE=" + sysroot_archive_generator_image_tag,
        "--file=" + str(sysroot_archive_dockerfile),
        "--output=type=local,dest=" + str(ctx.path(".")),
        sysroot_archive_dockerfile.dirname,
    ]

    script_result = ctx.execute(script_args)

    if script_result.return_code != 0:
        fail(("Dockerfile build failed: \nSTDOUT:\n%sSTDERR:\n%s") % (
            script_result.stdout,
            script_result.stderr,
        ))

    output_archive_name = "sysroot.tar.gz"
    generated_archive_path = ctx.path(output_archive_name)

    if not generated_archive_path.exists:
        fail(("Dockerfile build did not produce the expected archive at %s") % (
            str(generated_archive_path),
        ))

    if ctx.attr.sha256:
        sha256_result = ctx.execute(["sha256sum", str(generated_archive_path)])
        if sha256_result.return_code != 0:
            fail(("Failed to calculate sha256sum for %s: %s") % (
                generated_archive_path,
                sha256_result.stderr,
            ))

        calculated_sha256 = sha256_result.stdout.split(" ")[0].strip()
        if calculated_sha256 != ctx.attr.sha256:
            fail(
                ("SHA256 mismatch for generated archive %s. Expected: '%s', Got: '%s'. " +
                 "Please update the sha256 attribute in your MODULE.bazel or WORKSPACE file.") % (
                    output_archive_name,
                    ctx.attr.sha256,
                    calculated_sha256,
                ),
            )

    ctx.extract(
        archive = generated_archive_path,
        output = ".",
    )

    build_file_content = """
filegroup(
    name = "files",
    srcs = glob(["**"]),
    visibility = ["//visibility:public"],
)
"""
    ctx.file("BUILD.bazel", content = build_file_content, executable = False)

local_archive = repository_rule(
    implementation = _local_archive_impl,
    attrs = {
        "config": attr.label(
            mandatory = True,
            doc = "Path to the devkit.json file.",
            allow_single_file = True,
        ),
        "sha256": attr.string(
            mandatory = True,
            doc = "Expected SHA256 hash of the generated archive.",
        ),
    },
)
