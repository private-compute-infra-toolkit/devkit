#!/usr/bin/env python3
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

"""Test cases for the build script"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, List, Optional, Type, Union
from unittest.mock import ANY, MagicMock, call, patch

# Ensure the package root is in the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.docker import build


class TestBuildScript(unittest.TestCase):
    """Test suite for the build script."""

    def setUp(self) -> None:
        """Set up for tests."""
        self.test_dir = tempfile.mkdtemp()
        self.context_path = self.test_dir
        self.config_path = os.path.join(self.test_dir, "devkit.json")
        self.deps_path = os.path.join(self.test_dir, "deps.json")

        self.patcher_run = patch("subprocess.run")
        self.mock_run = self.patcher_run.start()

        self.patcher_stderr = patch("sys.stderr")
        self.mock_stderr = self.patcher_stderr.start()

        self.patcher_logging_info = patch("logging.info")
        self.mock_logging_info = self.patcher_logging_info.start()

        self.patcher_logging_warning = patch("logging.warning")
        self.mock_logging_warning = self.patcher_logging_warning.start()

        self.patcher_logging_error = patch("logging.error")
        self.mock_logging_error = self.patcher_logging_error.start()

        self.original_repo = build.REPO
        self.original_extra_packages_map = build.EXTRA_PACKAGES_MAP.copy()
        build.EXTRA_PACKAGES_MAP.clear()
        self.original_extra_keys_map = build.EXTRA_KEYS_MAP.copy()
        build.EXTRA_KEYS_MAP.clear()
        self.original_extra_repositories_map = build.EXTRA_REPOSITORIES_MAP.copy()
        build.EXTRA_REPOSITORIES_MAP.clear()

    def tearDown(self) -> None:
        """Tear down after tests."""
        shutil.rmtree(self.test_dir)
        patch.stopall()
        build.REPO = self.original_repo
        build.EXTRA_PACKAGES_MAP = self.original_extra_packages_map
        build.EXTRA_KEYS_MAP = self.original_extra_keys_map
        build.EXTRA_REPOSITORIES_MAP = self.original_extra_repositories_map

    # --- Helpers ---

    def _create_devkit_json(self, config: Any = None) -> None:
        """Helper to write devkit.json file."""
        if config is None:
            config = {
                "docker": {
                    "registry": {
                        "host": "my-registry",
                        "project": "project",
                        "repository": "repo",
                    }
                }
            }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)

    def _create_dockerfile(
        self,
        image_name: str,
        content: str,
        build_args_for_sha: Optional[List[str]] = None,
    ) -> tuple[str, str, str]:
        """Creates a Dockerfile and calculates its content-addressable tag."""
        dockerfile_path = os.path.join(self.test_dir, f"{image_name}.Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(content)

        hasher = hashlib.sha256()
        with open(dockerfile_path, "rb") as f:
            hasher.update(f.read())

        if build_args_for_sha:
            for arg in sorted(build_args_for_sha):
                hasher.update(arg.encode("utf-8"))

        sha = hasher.hexdigest()
        tag = f"my-registry/project/repo/devkit/{image_name}:amd64-{sha}"
        return dockerfile_path, tag, sha

    def _create_deps_json(self, deps_config: Any) -> None:
        """Helper to write deps.json file."""
        with open(self.deps_path, "w", encoding="utf-8") as f:
            json.dump(deps_config, f)

    def _call_docker_version(self, rc: Any = 0) -> tuple[tuple[str, ...], int]:
        return (("docker", "--version"), rc)

    def _call_buildx_version(self, rc: Any = 0) -> tuple[tuple[str, ...], int]:
        return (("docker", "buildx", "version"), rc)

    def _call_inspect_image(
        self, tag: Any, rc: Union[int, Type[Exception]] = 1
    ) -> tuple[tuple[str, ...], Union[int, Type[Exception]]]:
        return (("docker", "image", "inspect", tag), rc)

    def _call_inspect_manifest(
        self, tag: str, rc: int = 1
    ) -> tuple[tuple[str, ...], int]:
        return (("docker", "manifest", "inspect", tag), rc)

    def _call_build(
        self, tag: Any, dockerfile: Any, context: Any, rc: int = 0
    ) -> tuple[tuple[str, ...], int]:
        return (
            (
                "docker",
                "buildx",
                "build",
                "--tag",
                tag,
                "--file",
                dockerfile,
                context,
            ),
            rc,
        )

    def _call_push(self, tag: str, rc: int = 0) -> tuple[tuple[str, ...], int]:
        return (("docker", "push", tag), rc)

    def _call_pull(self, tag: str, rc: int = 0) -> tuple[tuple[str, ...], int]:
        return (("docker", "pull", tag), rc)

    def _mock_docker_calls(self, *responses: tuple[Any, Any]) -> None:
        """Helper to mock docker command results."""
        responses_data = list(responses)

        def side_effect(cmd: Any, **kwargs: Any) -> MagicMock:
            # build.py uses lists for all commands
            cmd_list = cmd
            cmd_tuple = tuple(cmd_list)

            for pattern, res in responses_data:
                if pattern == cmd_tuple:
                    if isinstance(res, type) and issubclass(res, Exception):
                        raise res
                    if res != 0 and kwargs.get("check"):
                        raise subprocess.CalledProcessError(
                            res, cmd_list, output="output", stderr="stderr"
                        )
                    return MagicMock(returncode=res, stdout="stdout", stderr="stderr")

            return MagicMock(returncode=0, stdout="stdout", stderr="stderr")

        self.mock_run.side_effect = side_effect

    def _run_main(
        self,
        target_image: Optional[str] = None,
        log_file: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        config_path: Optional[str] = None,
    ) -> None:
        """Helper to patch sys.argv and run the main build script."""
        if log_file is None:
            log_file = os.path.join(self.test_dir, "build.log")

        if config_path is None:
            config_path = self.config_path

        args = [
            "build.py",
            "--search-path",
            self.test_dir,
            "--config",
            config_path,
            "--log-file",
            log_file,
        ]
        if extra_args:
            args.extend(extra_args)
        if target_image:
            args.insert(1, target_image)

        with patch("sys.argv", args):
            build.main()

    # --- Expectation Helpers ---

    def _expect_docker_version(self) -> Any:
        """Expected call for docker --version check."""
        return call(["docker", "--version"], check=True, capture_output=True)

    def _expect_buildx_version(self) -> Any:
        """Expected call for docker buildx version check."""
        return call(["docker", "buildx", "version"], check=True, capture_output=True)

    def _expect_inspect_image(self, tag: str) -> Any:
        """Expected call for docker image inspect."""
        return call(
            ["docker", "image", "inspect", tag],
            capture_output=True,
            text=True,
            check=False,
        )

    def _expect_inspect_manifest(self, tag: str) -> Any:
        """Expected call for docker manifest inspect."""
        return call(
            ["docker", "manifest", "inspect", tag],
            capture_output=True,
            text=True,
            check=False,
        )

    def _expect_build(
        self,
        tag: str,
        dockerfile: str,
        context: Optional[str] = None,
        build_args: Optional[List[str]] = None,
    ) -> Any:
        """Expected call for docker buildx build."""
        if context is None:
            context = self.context_path
        cmd = ["docker", "buildx", "build", "--tag", tag, "--file", dockerfile]
        if build_args:
            for i in range(0, len(build_args), 2):
                cmd.append("--build-arg")
                cmd.append(f"{build_args[i]}={build_args[i + 1]}")

        cmd.append(context)

        return call(cmd, check=True, text=True, capture_output=True)

    def _expect_push(self, tag: str) -> Any:
        """Expected call for docker push."""
        return call(
            ["docker", "push", tag],
            check=False,
            text=True,
            capture_output=True,
        )

    def _expect_pull(self, tag: str) -> Any:
        """Expected call for docker pull."""
        return call(
            ["docker", "pull", tag],
            check=True,
            text=True,
            capture_output=True,
        )

    # --- Verification Helpers ---

    def _verify_docker_calls(self, *expected_calls: Any) -> None:
        """Helper to verify all docker calls."""
        self.assertEqual(self.mock_run.call_args_list, list(expected_calls))

    def _verify_log_info(self, msg: str, *args: Any) -> None:
        """Helper to verify logging.info calls."""
        self.mock_logging_info.assert_any_call(msg, *args)

    def _verify_log_warning(self, msg: str, *args: Any) -> None:
        """Helper to verify logging.warning calls."""
        self.mock_logging_warning.assert_any_call(msg, *args)

    def _verify_log_error(self, msg: str, *args: Any) -> None:
        """Helper to verify logging.error calls."""
        self.mock_logging_error.assert_any_call(msg, *args)

    def _verify_stderr(self, msg: str) -> None:
        """Helper to verify stderr writes."""
        self.mock_stderr.write.assert_any_call(msg)

    # --- Tests: Prerequisites ---

    def test_check_docker_not_installed(self) -> None:
        """Test failure when docker is not installed."""
        self._mock_docker_calls(self._call_docker_version(FileNotFoundError))

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        error_msg = "Docker is not installed or not in PATH. Please install Docker."
        self._verify_log_error(error_msg)
        self._verify_stderr(f"ERROR: {error_msg}")

    def test_check_buildx_not_installed(self) -> None:
        """Test failure when buildx is not installed."""
        self._mock_docker_calls(self._call_buildx_version(FileNotFoundError))

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        error_msg = (
            "Docker Buildx is not installed or not enabled. "
            "Please install/enable Docker Buildx."
        )
        self._verify_log_error(error_msg)
        self._verify_stderr(f"ERROR: {error_msg}")

    # --- Tests: Configuration & Discovery ---

    def test_config_missing_file_logs_info(self) -> None:
        """Test that missing devkit.json is handled gracefully."""
        # No devkit.json created
        self._create_deps_json({})
        self._mock_docker_calls()

        self._run_main(config_path="nonexistent.json")

        self._verify_log_info("devkit.json config file not found: %s", ANY)

    def test_config_invalid_json_exits(self) -> None:
        """Test exit on invalid devkit.json."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json")

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Could not load %s: %s", self.config_path, ANY)

    def test_config_schema_invalid_type(self) -> None:
        """Test exit on config with invalid type."""
        self._create_devkit_json({"docker": "not-a-dict"})

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Could not load %s: %s", self.config_path, ANY)
        call_args = self.mock_logging_error.call_args
        self.assertIsInstance(call_args[0][2], ValueError)
        self.assertIn("Invalid type at 'docker'", str(call_args[0][2]))

    def test_config_schema_extra_fields(self) -> None:
        """Test exit on config with extra fields."""
        self._create_devkit_json({"docker": {}, "extra_field": "value"})

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Could not load %s: %s", self.config_path, ANY)

        call_args = self.mock_logging_error.call_args
        self.assertIsInstance(call_args[0][2], ValueError)
        self.assertIn("Unexpected fields at ''", str(call_args[0][2]))
        self.assertIn("extra_field", str(call_args[0][2]))

    def test_config_with_run_property(self) -> None:
        """Test config with valid 'run' property."""
        self._create_devkit_json({"docker": {"run": ["--env=KEY=VALUE"]}})
        self._create_deps_json({})
        self._mock_docker_calls()

        # Should run without error
        self._run_main()

    def test_config_invalid_run_type(self) -> None:
        """Test exit on config with invalid 'run' type."""
        self._create_devkit_json({"docker": {"run": "not-a-list"}})

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Could not load %s: %s", self.config_path, ANY)

        call_args = self.mock_logging_error.call_args
        self.assertIsInstance(call_args[0][2], ValueError)
        self.assertIn("Invalid type at 'docker.run'", str(call_args[0][2]))

    def test_deps_invalid_json_exits(self) -> None:
        """Test exit on invalid deps.json."""
        self._create_devkit_json()
        with open(self.deps_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json")

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Could not decode %s: %s", self.deps_path, ANY)

    def test_deps_not_dict_logs_warning(self) -> None:
        """Test warning when deps.json is not a dict."""
        self._create_devkit_json()
        with open(self.deps_path, "w", encoding="utf-8") as f:
            f.write("[]")
        self._mock_docker_calls()

        self._run_main()

        self._verify_log_warning(
            "%s does not contain a dict of configs.", self.deps_path
        )

    def test_discovery_dockerfile_not_found(self) -> None:
        """Test exit when Dockerfile is missing for a defined image."""
        self._create_devkit_json()
        self._create_deps_json({"test-image": {"deps": {}}})
        self._mock_docker_calls()

        with self.assertRaises(SystemExit) as cm:
            self._run_main("test-image")

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error(
            "Dockerfile %s not found for image '%s' in any of the search paths: %s.",
            "test-image.Dockerfile",
            "test-image",
            [self.test_dir],
        )

    def test_discovery_no_project_root(self) -> None:
        """Test that main handles missing project root gracefully (relative config)."""
        self._create_devkit_json()
        self._create_deps_json({})

        cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            # Ensure devkit dir does not exist
            self.assertFalse(os.path.exists("devkit"))

            self._mock_docker_calls(
                self._call_docker_version(), self._call_buildx_version()
            )

            self._run_main(config_path="devkit.json")
        finally:
            os.chdir(cwd)

    def test_print_tag_requires_target(self) -> None:
        """Test that --print-tag fails if no target image is provided."""
        self._create_devkit_json()
        self._create_deps_json({"test-image": {"deps": {}}})
        self._mock_docker_calls(
            self._call_docker_version(), self._call_buildx_version()
        )

        with self.assertRaises(SystemExit) as cm:
            self._run_main(extra_args=["--print-tag"])

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("--print-tag requires a target_image to be specified.")

    def test_print_tag_invalid_target(self) -> None:
        """Test that --print-tag fails if the target image is invalid."""
        self._create_devkit_json()
        self._create_deps_json({"test-image": {"deps": {}}})
        self._mock_docker_calls(
            self._call_docker_version(), self._call_buildx_version()
        )

        with self.assertRaises(SystemExit) as cm:
            self._run_main(target_image="invalid-image", extra_args=["--print-tag"])

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error(
            "Target image '%s' for --print-tag is not a valid image name.",
            "invalid-image",
        )

    def test_print_tag_success(self) -> None:
        """Test --print-tag successfully prints tag and exits."""
        self._create_devkit_json()
        _, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}}})

        # Use empty mock to trigger default return (rc=0) for all calls
        # This covers the fallback return in side_effect
        self._mock_docker_calls()

        with patch("builtins.print") as mock_print:
            with self.assertRaises(SystemExit) as cm:
                self._run_main("test-image", extra_args=["--print-tag"])
            self.assertEqual(cm.exception.code, 0)
            mock_print.assert_any_call(tag)

    # --- Tests: Dependency Logic ---

    def test_dependency_cycle_detection(self) -> None:
        """Test that a dependency cycle causes exit."""
        self._create_devkit_json()
        deps_config = {
            "A": {"deps": {"dep1": "B"}},
            "B": {"deps": {"dep2": "A"}},
        }
        self._create_deps_json(deps_config)
        self._create_dockerfile("A", "FROM scratch")
        self._create_dockerfile("B", "FROM scratch")

        with self.assertRaises(SystemExit) as cm:
            self._run_main()

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Cycle detected in image dependencies: %s", ANY)

    # --- Tests: Build Scenarios ---

    def test_build_local_skip_if_exists(self) -> None:
        """
        Scenario: Image exists locally.
        Expected: No build, no pull, no push.
        """
        self._create_devkit_json()
        _, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}, "local": False}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 0),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
        )
        self._verify_log_info("Image %s already exists locally.", tag)

    def test_build_local_only_success(self) -> None:
        """
        Scenario: No registry configured (local only build).
        Expected: Build, no push.
        """
        self._create_devkit_json({})  # No registry
        dockerfile_path, _, sha = self._create_dockerfile("test-image", "FROM scratch")
        # Tag format changes when no repo is configured
        tag = f"devkit/test-image:amd64-{sha}"

        self._create_deps_json({"test-image": {"deps": {}}})
        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_build(tag, dockerfile_path),
        )
        self._verify_stderr(f"Building image: {tag}...")

    def test_build_pulls_if_remote_exists(self) -> None:
        """
        Scenario: Image missing locally, but exists in remote registry.
        Expected: Pull image.
        """
        self._create_devkit_json()
        _, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}, "local": False}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 0),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_inspect_manifest(tag),
            self._expect_pull(tag),
        )
        self._verify_stderr(f"Pulling image: {tag}...")

    def test_build_and_push_if_missing_remote(self) -> None:
        """
        Scenario: Image missing locally and remotely.
        Expected: Build and push.
        """
        self._create_devkit_json()
        dockerfile_path, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 1),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_inspect_manifest(tag),
            self._expect_build(tag, dockerfile_path),
            self._expect_push(tag),
        )
        self._verify_stderr(f"Building image: {tag}...")
        self._verify_stderr(f"Pushing image: {tag}...")

    def test_build_local_mode_skips_push(self) -> None:
        """
        Scenario: local=True configured.
        Expected: Build, no check for remote, no push.
        """
        self._create_devkit_json()
        dockerfile_path, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}, "local": True}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_build(tag, dockerfile_path),
        )
        self._verify_stderr(f"Building image: {tag}...")

    def test_build_local_mode_warns_no_repo(self) -> None:
        """
        Scenario: local=True and no repo configured.
        Expected: Warning logged, build proceeds.
        """
        self._create_devkit_json({})
        dockerfile_path, _, sha = self._create_dockerfile("test-image", "FROM scratch")
        tag = f"devkit/test-image:amd64-{sha}"

        self._create_deps_json({"test-image": {"deps": {}, "local": True}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
        )

        self._run_main("test-image")

        self._verify_log_warning("Docker registry is not defined.")
        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_build(tag, dockerfile_path),
        )

    def test_build_dependency_chain(self) -> None:
        """
        Scenario: Target 'child' depends on 'parent'. Both missing.
        Expected: Build/push parent, then build/push child with build-arg.
        """
        self._create_devkit_json()
        parent_df, parent_tag, _ = self._create_dockerfile("parent", "FROM scratch")
        child_df, child_tag, _ = self._create_dockerfile(
            "child", "ARG BASE\nFROM ${BASE}\n", [f"BASE={parent_tag}"]
        )
        self._create_deps_json(
            {
                "parent": {"deps": {}},
                "child": {"deps": {"BASE": "parent"}},
            }
        )

        self._mock_docker_calls(
            self._call_inspect_image(parent_tag, 1),
            self._call_inspect_manifest(parent_tag, 1),
            self._call_inspect_image(child_tag, 1),
            self._call_inspect_manifest(child_tag, 1),
        )

        self._run_main("child")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            # Parent
            self._expect_inspect_image(parent_tag),
            self._expect_inspect_manifest(parent_tag),
            self._expect_build(parent_tag, parent_df),
            self._expect_push(parent_tag),
            # Child
            self._expect_inspect_image(child_tag),
            self._expect_inspect_manifest(child_tag),
            self._expect_build(child_tag, child_df, build_args=["BASE", parent_tag]),
            self._expect_push(child_tag),
        )

    def test_build_all_images(self) -> None:
        """
        Scenario: No target specified.
        Expected: Build all defined images.
        """
        self._create_devkit_json()
        dockerfile_path, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 1),
        )

        self._run_main()  # No target

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_inspect_manifest(tag),
            self._expect_build(tag, dockerfile_path),
            self._expect_push(tag),
        )

    def test_build_with_packages(self) -> None:
        """
        Scenario: packages defined in devkit.json.
        Expected: Build arg EXTRA_PACKAGES passed, SHA includes it.
        """
        self._create_devkit_json(
            {
                "docker": {
                    "registry": {
                        "host": "my-registry",
                        "project": "project",
                        "repository": "repo",
                    },
                    "images": {
                        "test-image": {"packages": {"pkg1": "1.0", "pkg2": "2.0"}}
                    },
                }
            }
        )

        # Manually calculate expected SHA with EXTRA_PACKAGES
        dockerfile_content = "FROM scratch"
        dockerfile_path = os.path.join(self.test_dir, "test-image.Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        hasher = hashlib.sha256()
        with open(dockerfile_path, "rb") as f:
            hasher.update(f.read())

        # The script sorts build args for SHA calc.
        # It adds "EXTRA_PACKAGES=pkg1=1.0 pkg2=2.0"
        hasher.update(b"EXTRA_PACKAGES=pkg1=1.0 pkg2=2.0")

        sha = hasher.hexdigest()
        tag = f"my-registry/project/repo/devkit/test-image:amd64-{sha}"

        self._create_deps_json({"test-image": {"deps": {}}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 1),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_inspect_manifest(tag),
            self._expect_build(
                tag,
                dockerfile_path,
                build_args=["EXTRA_PACKAGES", "pkg1=1.0 pkg2=2.0"],
            ),
            self._expect_push(tag),
        )

    def test_build_with_gpg_and_repos(self) -> None:
        """
        Scenario: gpg_keys and repositories defined in devkit.json.
        Expected: Build args EXTRA_KEYS and EXTRA_REPOSITORIES passed.
        """
        self._create_devkit_json(
            {
                "docker": {
                    "registry": {
                        "host": "my-registry",
                        "project": "project",
                        "repository": "repo",
                    },
                    "images": {
                        "test-image": {
                            "keys": {"key1": "url1", "key2": "url2"},
                            "repositories": {"repo1": "url1", "repo2": "url2"},
                        }
                    },
                }
            }
        )

        dockerfile_content = "FROM scratch"
        dockerfile_path = os.path.join(self.test_dir, "test-image.Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        hasher = hashlib.sha256()
        with open(dockerfile_path, "rb") as f:
            hasher.update(f.read())

        # Keys in gpg_keys are stored as "name=url"
        hasher.update(b"EXTRA_KEYS=key1=url1 key2=url2")
        hasher.update(b"EXTRA_REPOSITORIES=repo1=url1 repo2=url2")

        sha = hasher.hexdigest()
        tag = f"my-registry/project/repo/devkit/test-image:amd64-{sha}"

        self._create_deps_json({"test-image": {"deps": {}}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 1),
        )

        self._run_main("test-image")

        self._verify_docker_calls(
            self._expect_docker_version(),
            self._expect_buildx_version(),
            self._expect_inspect_image(tag),
            self._expect_inspect_manifest(tag),
            self._expect_build(
                tag,
                dockerfile_path,
                build_args=[
                    "EXTRA_KEYS",
                    "key1=url1 key2=url2",
                    "EXTRA_REPOSITORIES",
                    "repo1=url1 repo2=url2",
                ],
            ),
            self._expect_push(tag),
        )

    def test_build_with_empty_package_version(self) -> None:
        """
        Scenario: packages defined in devkit.json with an empty version.
        Expected: Exit with error.
        """
        self._create_devkit_json(
            {
                "docker": {
                    "registry": {
                        "host": "my-registry",
                        "project": "project",
                        "repository": "repo",
                    },
                    "images": {"test-image": {"packages": {"pkg1": ""}}},
                }
            }
        )
        self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}}})

        with self.assertRaises(SystemExit) as cm:
            self._run_main("test-image")

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error(
            "Package %s in image %s has an empty version. "
            "Please specify a version or use '*'.",
            "pkg1",
            "test-image",
        )

    # --- Tests: Execution Errors ---

    def test_execution_build_failure(self) -> None:
        """Test handling of docker build failure."""
        self._create_devkit_json()
        dockerfile_path, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}}})

        # Build fails
        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 1),
            self._call_build(
                tag,
                os.path.realpath(dockerfile_path),
                os.path.dirname(os.path.realpath(dockerfile_path)),
                1,
            ),
        )

        with self.assertRaises(SystemExit) as cm:
            self._run_main("test-image")

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Error during Docker operation for %s:", tag)
        self._verify_log_error("Stderr: %s", "stderr")

    def test_push_failure_handling(self) -> None:
        """Test handling of docker push failure."""
        self._create_devkit_json()
        dockerfile_path, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 1),
            self._call_build(tag, os.path.realpath(dockerfile_path), self.test_dir, 0),
            self._call_push(tag, 1),  # Push fails
        )

        # Should not exit with 1, but log warning and continue (exit 0 implied)
        self._run_main("test-image")

        self._verify_log_warning(
            "Failed to push image %s. Continuing with local image.", tag
        )
        self._verify_log_warning("Details: %s", "stderr")

    def test_pull_failure_handling(self) -> None:
        """Test handling of docker pull failure."""
        self._create_devkit_json()
        _, tag, _ = self._create_dockerfile("test-image", "FROM scratch")
        self._create_deps_json({"test-image": {"deps": {}, "local": False}})

        self._mock_docker_calls(
            self._call_inspect_image(tag, 1),
            self._call_inspect_manifest(tag, 0),
            self._call_pull(tag, 1),  # Pull fails
        )

        with self.assertRaises(SystemExit) as cm:
            self._run_main("test-image")

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Error during Docker operation for %s:", tag)

    def test_dependency_cycle_in_subgraph(self) -> None:
        """Test dependency cycle detection when building specific target."""
        self._create_devkit_json()
        self._create_deps_json({"A": {"deps": {"d": "B"}}, "B": {"deps": {"d": "A"}}})
        self._create_dockerfile("A", "")
        self._create_dockerfile("B", "")

        with self.assertRaises(SystemExit) as cm:
            self._run_main("A")

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error("Cycle detected in dependencies for %s: %s", "A", ANY)

    def test_invalid_target_image(self) -> None:
        """Test invalid target image provided to main."""
        self._create_devkit_json()
        self._create_deps_json({})

        with self.assertRaises(SystemExit) as cm:
            self._run_main("invalid")

        self.assertEqual(cm.exception.code, 1)
        self._verify_log_error(
            "Specified target image '%s' is not a valid image name.", "invalid"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
