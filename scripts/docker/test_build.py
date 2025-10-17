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
import os
import subprocess
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, mock_open, patch
import graphlib

# Ensure the package root is in the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.docker import build


class SysExitCalled(Exception):
    """Exception to be raised when sys.exit is called."""


class TestBuildScript(unittest.TestCase):
    """Test suite for the docker build script."""

    def setUp(self) -> None:
        """Set up for tests."""
        build.REPO = ""
        # This is to prevent sys.exit from stopping the test runner
        self.mock_sys_exit = patch("sys.exit", side_effect=SysExitCalled).start()

    def tearDown(self) -> None:
        """Tear down after tests."""
        patch.stopall()

    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_find_project_root_not_found(
        self, mock_getcwd: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test find_project_root when devkit is not found."""
        mock_getcwd.return_value = "/a/b/c"
        mock_exists.return_value = False
        root = build.find_project_root()
        self.assertIsNone(root)
        expected_calls = [
            call(os.path.join("/a/b/c", "devkit")),
            call(os.path.join("/a/b", "devkit")),
            call(os.path.join("/a", "devkit")),
            call(os.path.join("/", "devkit")),
        ]
        mock_exists.assert_has_calls(expected_calls)

    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_find_project_root_in_parent(
        self, mock_getcwd: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test find_project_root when devkit is in a parent directory."""
        mock_getcwd.return_value = "/a/b/c"
        mock_exists.side_effect = [False, True]
        root = build.find_project_root()
        self.assertEqual(root, "/a/b")
        expected_calls = [
            call(os.path.join("/a/b/c", "devkit")),
            call(os.path.join("/a/b", "devkit")),
        ]
        mock_exists.assert_has_calls(expected_calls)

    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_find_project_root_in_current_dir(
        self, mock_getcwd: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test find_project_root when devkit is in the current directory."""
        mock_getcwd.return_value = "/a/b/c"
        mock_exists.return_value = True
        root = build.find_project_root()
        self.assertEqual(root, "/a/b/c")
        mock_exists.assert_called_once_with(os.path.join("/a/b/c", "devkit"))

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"docker": {"registry": '
        '{"host": "my-host", "project": "my-project", "repository": "my-repo"}}}',
    )
    def test_load_config_success(
        self, unused_mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test load_config successfully loads registry."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "my-host/my-project/my-repo")
        mock_exists.assert_called_once_with("dummy/path/devkit.json")

    @patch("os.path.exists", return_value=False)
    def test_load_config_not_exists(self, mock_exists: MagicMock) -> None:
        """Test load_config does nothing if file doesn't exist."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "")
        mock_exists.assert_called_once_with("dummy/path/devkit.json")

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{"docker": {}}')
    def test_load_config_no_registry(
        self, unused_mock_file: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test load_config with no registry key."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "")

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"docker": {"registry": '
        '{"project": "my-project", "repository": "my-repo"}}}',
    )
    def test_load_config_no_host(
        self, unused_mock_file: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test load_config with a registry object missing the host."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "")

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"docker": {"registry": '
        '{"host": "my-host", "repository": "my-repo"}}}',
    )
    def test_load_config_no_project(
        self, unused_mock_file: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test load_config with a registry object missing the project."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "")

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"docker": {"registry": '
        '{"host": "my-host", "project": "my-project"}}}',
    )
    def test_load_config_no_repository(
        self, unused_mock_file: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test load_config with a registry object missing the repository."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "")

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"docker": {"registry": '
        '{"host": "", "project": "", "repository": ""}}}',
    )
    def test_load_config_with_empty_strings(
        self, unused_mock_file: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test load_config with a registry object with empty strings."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "")

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("logging.error")
    def test_load_config_json_decode_error(
        self,
        mock_log_error: MagicMock,
        unused_mock_file: MagicMock,
        unused_mock_exists: MagicMock,
    ) -> None:
        """Test load_config with JSON decode error."""
        with self.assertRaises(SysExitCalled):
            build.load_config("dummy/path/devkit.json")
        self.mock_sys_exit.assert_called_once_with(1)
        mock_log_error.assert_called_once_with(
            "Could not decode %s: %s",
            "dummy/path/devkit.json",
            unittest.mock.ANY,
        )

    @patch("os.path.join")
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"image1": {"deps": {}}}',
    )
    def test_load_image_configs_success(
        self, mock_file: MagicMock, mock_exists: MagicMock, mock_join: MagicMock
    ) -> None:
        """Test load_image_configs successfully loads configs."""
        mock_join.return_value = "search/path/deps.json"
        mock_exists.return_value = True
        configs = build.load_image_configs(["search/path"])
        self.assertEqual(configs, {"image1": {"deps": {}}})
        mock_join.assert_called_once_with("search/path", "deps.json")
        mock_exists.assert_called_once_with("search/path/deps.json")
        mock_file.assert_called_once_with(
            "search/path/deps.json", "r", encoding="utf-8"
        )

    @patch("os.path.join")
    @patch("os.path.exists", return_value=False)
    def test_load_image_configs_no_deps_file(
        self, unused_mock_exists: MagicMock, unused_mock_join: MagicMock
    ) -> None:
        """Test load_image_configs when deps.json does not exist."""
        configs = build.load_image_configs(["search/path"])
        self.assertEqual(configs, {})

    @patch("os.path.join")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="[1, 2, 3]")
    @patch("logging.warning")
    def test_load_image_configs_not_a_dict(
        self,
        mock_log_warning: MagicMock,
        unused_mock_file: MagicMock,
        unused_mock_exists: MagicMock,
        mock_join: MagicMock,
    ) -> None:
        """Test load_image_configs with non-dict JSON content."""
        mock_join.return_value = "search/path/deps.json"
        configs = build.load_image_configs(["search/path"])
        self.assertEqual(configs, {})
        mock_log_warning.assert_any_call(
            "%s does not contain a dict of configs.", "search/path/deps.json"
        )

    @patch("os.path.join")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("logging.error")
    def test_load_image_configs_json_decode_error(
        self,
        mock_log_error: MagicMock,
        unused_mock_file: MagicMock,
        unused_mock_exists: MagicMock,
        mock_join: MagicMock,
    ) -> None:
        """Test load_image_configs with JSON decode error."""
        mock_join.return_value = "search/path/deps.json"
        with self.assertRaises(SysExitCalled):
            build.load_image_configs(["search/path"])
        self.mock_sys_exit.assert_called_once_with(1)
        mock_log_error.assert_called_once_with(
            "Could not decode %s: %s",
            "search/path/deps.json",
            unittest.mock.ANY,
        )

    @patch("builtins.open", new_callable=mock_open, read_data=b"dockerfile content")
    def test_calculate_sha256(self, unused_mock_file: MagicMock) -> None:
        """Test calculate_sha256."""
        sha = build.calculate_sha256("Dockerfile", ["ARG1=val1", "ARG2=val2"])
        expected_sha = hashlib.sha256(
            b"dockerfile content" + b"ARG1=val1" + b"ARG2=val2"
        ).hexdigest()
        self.assertEqual(sha, expected_sha)

    def test_get_image_tag_with_repo(self) -> None:
        """Test get_image_tag with REPO set."""
        build.REPO = "my-repo"
        tag = build.get_image_tag("image-name", "12345")
        self.assertEqual(tag, "my-repo/devkit/image-name:amd64-12345")

    def test_get_image_tag_without_repo(self) -> None:
        """Test get_image_tag without REPO set."""
        tag = build.get_image_tag("image-name", "12345")
        self.assertEqual(tag, "devkit/image-name:amd64-12345")

    @patch("scripts.docker.build.push_image_to_registry")
    @patch("scripts.docker.build.build_image")
    @patch("scripts.docker.build.pull_image_from_registry")
    @patch("scripts.docker.build.check_if_image_exists_in_remote_registry")
    @patch("scripts.docker.build.check_if_image_exists_locally")
    def test_manage_docker_image_exists_locally(
        self,
        mock_check_local: MagicMock,
        mock_check_remote: MagicMock,
        mock_pull: MagicMock,
        mock_build: MagicMock,
        mock_push: MagicMock,
    ) -> None:
        """Test manage_docker_image when image exists locally."""
        mock_check_local.return_value = True
        build.manage_docker_image("tag", "Dockerfile", [], "context", False)
        mock_check_local.assert_called_once_with("tag")
        mock_check_remote.assert_not_called()
        mock_pull.assert_not_called()
        mock_build.assert_not_called()
        mock_push.assert_not_called()

    @patch("scripts.docker.build.push_image_to_registry")
    @patch("scripts.docker.build.build_image")
    @patch("scripts.docker.build.pull_image_from_registry")
    @patch("scripts.docker.build.check_if_image_exists_in_remote_registry")
    @patch("scripts.docker.build.check_if_image_exists_locally")
    def test_manage_docker_image_exists_remotely(
        self,
        mock_check_local: MagicMock,
        mock_check_remote: MagicMock,
        mock_pull: MagicMock,
        mock_build: MagicMock,
        mock_push: MagicMock,
    ) -> None:
        """Test manage_docker_image when image exists remotely and is pulled."""
        mock_check_local.return_value = False
        mock_check_remote.return_value = True
        build.manage_docker_image("tag", "Dockerfile", [], "context", False)
        mock_check_local.assert_called_once_with("tag")
        mock_check_remote.assert_called_once_with("tag")
        mock_pull.assert_called_once_with("tag")
        mock_build.assert_not_called()
        mock_push.assert_not_called()

    @patch("scripts.docker.build.push_image_to_registry")
    @patch("scripts.docker.build.build_image")
    @patch("scripts.docker.build.pull_image_from_registry")
    @patch("scripts.docker.build.check_if_image_exists_in_remote_registry")
    @patch("scripts.docker.build.check_if_image_exists_locally")
    def test_manage_docker_image_build_and_push_success(
        self,
        mock_check_local: MagicMock,
        mock_check_remote: MagicMock,
        mock_pull: MagicMock,
        mock_build: MagicMock,
        mock_push: MagicMock,
    ) -> None:
        """Test manage_docker_image builds and pushes when image does not exist."""
        mock_check_local.return_value = False
        mock_check_remote.return_value = False
        build.manage_docker_image("tag", "Dockerfile", ["ARG", "val"], "context", False)
        mock_check_local.assert_called_once_with("tag")
        mock_check_remote.assert_called_once_with("tag")
        mock_pull.assert_not_called()
        mock_build.assert_called_once_with(
            "tag", "Dockerfile", ["ARG", "val"], "context"
        )
        mock_push.assert_called_once_with("tag")

    @patch("scripts.docker.build.check_if_image_exists_locally", return_value=False)
    @patch(
        "scripts.docker.build.check_if_image_exists_in_remote_registry",
        return_value=True,
    )
    @patch("scripts.docker.build.pull_image_from_registry")
    def test_manage_docker_image_called_process_error_on_pull(
        self,
        mock_pull: MagicMock,
        unused_mock_check_remote: MagicMock,
        unused_mock_check_local: MagicMock,
    ) -> None:
        """Test manage_docker_image with CalledProcessError during pull."""
        error = subprocess.CalledProcessError(2, "cmd")
        error.stdout = "out"
        error.stderr = "err"
        mock_pull.side_effect = error
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context", False)
        self.mock_sys_exit.assert_called_once_with(2)

    @patch("scripts.docker.build.check_if_image_exists_locally", return_value=False)
    @patch(
        "scripts.docker.build.check_if_image_exists_in_remote_registry",
        return_value=False,
    )
    @patch("scripts.docker.build.build_image")
    def test_manage_docker_image_called_process_error_on_build(
        self,
        mock_build: MagicMock,
        unused_mock_check_remote: MagicMock,
        unused_mock_check_local: MagicMock,
    ) -> None:
        """Test manage_docker_image with CalledProcessError during build."""
        error = subprocess.CalledProcessError(1, "cmd")
        error.stdout = "out"
        error.stderr = "err"
        mock_build.side_effect = error
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context", False)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("scripts.docker.build.check_if_image_exists_locally", return_value=False)
    @patch(
        "scripts.docker.build.check_if_image_exists_in_remote_registry",
        return_value=False,
    )
    @patch("scripts.docker.build.build_image")
    def test_manage_docker_image_called_process_error_with_zero_exit_code(
        self,
        mock_build: MagicMock,
        unused_mock_check_remote: MagicMock,
        unused_mock_check_local: MagicMock,
    ) -> None:
        """Test manage_docker_image with CalledProcessError and exit code 0."""
        error = subprocess.CalledProcessError(0, "cmd")
        mock_build.side_effect = error
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context", False)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("scripts.docker.build.check_if_image_exists_locally", return_value=False)
    @patch(
        "scripts.docker.build.check_if_image_exists_in_remote_registry",
        return_value=False,
    )
    @patch("scripts.docker.build.build_image", side_effect=FileNotFoundError)
    def test_manage_docker_image_file_not_found_error(
        self,
        unused_mock_build: MagicMock,
        unused_mock_check_remote: MagicMock,
        unused_mock_check_local: MagicMock,
    ) -> None:
        """Test manage_docker_image with FileNotFoundError."""
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context", False)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("scripts.docker.build.build_image")
    @patch("scripts.docker.build.check_if_image_exists_locally")
    def test_manage_docker_image_local_mode_exists_locally(
        self, mock_check_local: MagicMock, mock_build: MagicMock
    ) -> None:
        """Test manage_docker_image in local mode when image exists locally."""
        mock_check_local.return_value = True
        build.manage_docker_image("tag", "Dockerfile", [], "context", True)
        mock_check_local.assert_called_once_with("tag")
        mock_build.assert_not_called()

    @patch("scripts.docker.build.push_image_to_registry")
    @patch("scripts.docker.build.build_image")
    @patch("scripts.docker.build.pull_image_from_registry")
    @patch("scripts.docker.build.check_if_image_exists_in_remote_registry")
    @patch("scripts.docker.build.check_if_image_exists_locally")
    def test_manage_docker_image_local_mode_builds(
        self,
        mock_check_local: MagicMock,
        mock_check_remote: MagicMock,
        mock_pull: MagicMock,
        mock_build: MagicMock,
        mock_push: MagicMock,
    ) -> None:
        """Test manage_docker_image in local mode builds, does not push."""
        mock_check_local.return_value = False
        build.manage_docker_image("tag", "Dockerfile", ["ARG", "val"], "context", True)
        mock_check_local.assert_called_once_with("tag")
        mock_build.assert_called_once_with(
            "tag", "Dockerfile", ["ARG", "val"], "context"
        )
        mock_check_remote.assert_not_called()
        mock_pull.assert_not_called()
        mock_push.assert_not_called()

    @patch("os.path.exists", return_value=False)
    def test_process_image_dockerfile_not_found(
        self, unused_mock_exists: MagicMock
    ) -> None:
        """Test process_image when Dockerfile is not found."""
        with self.assertRaises(SysExitCalled):
            build.process_image("image", {}, {}, False, None, ["search/path"], None)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    def test_process_image_dependency_not_found(
        self, unused_mock_realpath: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test process_image when a dependency tag is not found."""
        with self.assertRaises(SysExitCalled):
            build.process_image(
                "image", {"DEP": "dep-image"}, {}, False, None, ["search/path"], None
            )
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    @patch("scripts.docker.build.calculate_sha256", side_effect=FileNotFoundError)
    def test_process_image_calculate_sha_file_not_found(
        self,
        unused_mock_sha: MagicMock,
        unused_mock_realpath: MagicMock,
        unused_mock_exists: MagicMock,
    ) -> None:
        """Test process_image with FileNotFoundError during SHA calculation."""
        with self.assertRaises(SysExitCalled):
            build.process_image("image", {}, {}, False, None, ["search/path"], None)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    @patch("scripts.docker.build.calculate_sha256", return_value="sha123")
    @patch("scripts.docker.build.get_image_tag", return_value="tag123")
    @patch("scripts.docker.build.manage_docker_image")
    def test_process_image_success(
        self,
        mock_manage: MagicMock,
        mock_get_tag: MagicMock,
        mock_sha: MagicMock,
        unused_mock_realpath: MagicMock,
        unused_mock_exists: MagicMock,
    ) -> None:
        """Test process_image success path."""
        generated_tags: Dict[str, str] = {"dep-image": "dep-tag"}
        dependencies = {"DEP": "dep-image"}
        tag = build.process_image(
            "image", dependencies, generated_tags, False, None, ["search/path"], None
        )
        self.assertEqual(tag, "tag123")
        self.assertEqual(generated_tags["image"], "tag123")
        mock_sha.assert_called_once_with("/abs/path/to/Dockerfile", ["DEP=dep-tag"])
        mock_get_tag.assert_called_once_with("image", "sha123")
        mock_manage.assert_called_once_with(
            "tag123",
            "/abs/path/to/Dockerfile",
            ["DEP", "dep-tag"],
            "/abs/path/to",
            None,
        )

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    @patch("scripts.docker.build.calculate_sha256", return_value="sha123")
    @patch("scripts.docker.build.get_image_tag", return_value="tag123")
    @patch("scripts.docker.build.manage_docker_image")
    def test_process_image_print_tag_mode(
        self,
        unused_mock_manage: MagicMock,
        unused_mock_get_tag: MagicMock,
        unused_mock_sha: MagicMock,
        unused_mock_realpath: MagicMock,
        unused_mock_exists: MagicMock,
    ) -> None:
        """Test process_image with print_tag_mode enabled."""
        with self.assertRaises(SysExitCalled):
            build.process_image("image", {}, {}, True, "image", ["search/path"], None)
        self.mock_sys_exit.assert_called_once_with(0)

    def test_get_dependency_subgraph_target_not_in_map(self) -> None:
        """Test get_dependency_subgraph when target is not in the config map."""
        result = build.get_dependency_subgraph("target", {})
        self.assertEqual(result, [])

    def test_get_dependency_subgraph_success(self) -> None:
        """Test get_dependency_subgraph for a valid graph."""
        image_configs_map: Dict[str, build.ImageConfig] = {
            "a": {"deps": {"FROM": "b"}, "local": None},
            "b": {"deps": {"FROM": "c"}, "local": None},
            "c": {"deps": {}, "local": None},
            "d": {"deps": {}, "local": None},
        }
        result = build.get_dependency_subgraph("a", image_configs_map)
        self.assertEqual(result, ["c", "b", "a"])

    def test_get_dependency_subgraph_cycle(self) -> None:
        """Test get_dependency_subgraph with a cycle."""
        image_configs_map: Dict[str, build.ImageConfig] = {
            "a": {"deps": {"FROM": "b"}, "local": None},
            "b": {"deps": {"FROM": "a"}, "local": None},
        }
        with self.assertRaises(SysExitCalled):
            build.get_dependency_subgraph("a", image_configs_map)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    @patch("scripts.docker.build.get_dependency_subgraph")
    @patch("scripts.docker.build.process_image")
    def test_main_build_target(
        self,
        mock_process: MagicMock,
        mock_subgraph: MagicMock,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main function with a target image."""
        args = MagicMock(
            target_image="a",
            print_tag=False,
            config="conf",
            search_path=["path"],
            log_file=None,
        )
        mock_argparse.return_value.parse_args.return_value = args
        image_configs: build.ImageConfigsMap = {
            "a": {"deps": {}, "local": None},
            "b": {"deps": {}, "local": None},
        }
        mock_load_images.return_value = image_configs
        mock_subgraph.return_value = ["a"]
        build.main()
        mock_load_images.assert_called_once_with(["path"])
        mock_subgraph.assert_called_once_with("a", image_configs)
        mock_process.assert_called_once_with("a", {}, {}, False, None, ["path"], None)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    @patch("graphlib.TopologicalSorter")
    @patch("scripts.docker.build.process_image")
    def test_main_build_all(
        self,
        mock_process: MagicMock,
        mock_sorter: MagicMock,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main function building all images."""
        args = MagicMock(
            target_image=None,
            print_tag=False,
            config="conf",
            search_path=["path"],
            log_file=None,
        )
        mock_argparse.return_value.parse_args.return_value = args
        image_configs: build.ImageConfigsMap = {
            "a": {"deps": {"FROM": "b"}, "local": None},
            "b": {"deps": {}, "local": None},
        }
        mock_load_images.return_value = image_configs
        mock_sorter.return_value.static_order.return_value = ["b", "a"]

        actual_calls: List[Any] = []

        def process_image_side_effect(
            image_name: str,
            dependencies: Dict[str, str],
            gen_tags: Dict[str, str],
            print_tag_mode: bool,
            target_image_for_tag_print: str,
            search_paths: List[str],
            local_image_mode: Optional[bool],
        ) -> str:
            actual_calls.append(
                call(
                    image_name,
                    dependencies.copy(),
                    gen_tags.copy(),
                    print_tag_mode,
                    target_image_for_tag_print,
                    search_paths,
                    local_image_mode,
                )
            )
            tag = f"tag-for-{image_name}"
            gen_tags[image_name] = tag
            return tag

        mock_process.side_effect = process_image_side_effect

        build.main()

        mock_sorter.assert_called_once_with({"a": {"b"}, "b": set()})
        self.assertEqual(len(actual_calls), 2)
        expected_calls = [
            call("b", {}, {}, False, None, ["path"], None),
            call(
                "a",
                {"FROM": "b"},
                {"b": "tag-for-b"},
                False,
                None,
                ["path"],
                None,
            ),
        ]
        self.assertEqual(actual_calls, expected_calls)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    def test_main_print_tag_no_target(
        self,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main with --print-tag but no target."""
        args = MagicMock(target_image=None, print_tag=True)
        mock_argparse.return_value.parse_args.return_value = args
        mock_load_images.return_value = {}
        with self.assertRaises(SysExitCalled):
            build.main()
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    def test_main_print_tag_invalid_target(
        self,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main with --print-tag and invalid target."""
        args = MagicMock(target_image="c", print_tag=True)
        mock_argparse.return_value.parse_args.return_value = args
        mock_load_images.return_value = {"a": {}, "b": {}}
        with self.assertRaises(SysExitCalled):
            build.main()
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    def test_main_invalid_target(
        self,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main with an invalid target image."""
        args = MagicMock(target_image="c", print_tag=False)
        mock_argparse.return_value.parse_args.return_value = args
        mock_load_images.return_value = {"a": {}, "b": {}}
        with self.assertRaises(SysExitCalled):
            build.main()
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    @patch("graphlib.TopologicalSorter", side_effect=graphlib.CycleError("cycle"))
    def test_main_cycle_error(
        self,
        unused_mock_sorter: MagicMock,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main with a cycle in dependencies."""
        args = MagicMock(target_image=None, print_tag=False)
        mock_argparse.return_value.parse_args.return_value = args
        mock_load_images.return_value = {
            "a": {"deps": {"FROM": "b"}},
            "b": {"deps": {"FROM": "a"}},
        }
        with self.assertRaises(SysExitCalled):
            build.main()
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("argparse.ArgumentParser")
    @patch("scripts.docker.build.load_config")
    @patch("scripts.docker.build.load_image_configs")
    @patch("scripts.docker.build.get_dependency_subgraph")
    def test_main_print_tag_not_processed(
        self,
        mock_subgraph: MagicMock,
        mock_load_images: MagicMock,
        unused_mock_load_config: MagicMock,
        mock_argparse: MagicMock,
    ) -> None:
        """Test main with --print-tag where target is not processed."""
        args = MagicMock(
            target_image="a",
            print_tag=True,
            config="conf",
            search_path=["path"],
        )
        mock_argparse.return_value.parse_args.return_value = args
        mock_load_images.return_value = {"a": {"deps": {}}}
        mock_subgraph.return_value = []
        with self.assertRaises(SysExitCalled):
            build.main()
        self.mock_sys_exit.assert_called_once_with(1)


class TestDockerWrapperCommands(unittest.TestCase):
    """Test suite for docker command wrappers."""

    @patch("subprocess.run")
    def test_check_if_image_exists_locally_exists(self, mock_run: MagicMock) -> None:
        """Test check_if_image_exists_locally when image exists."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(build.check_if_image_exists_locally("tag"))
        mock_run.assert_called_once_with(
            ["docker", "image", "inspect", "tag"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_check_if_image_exists_locally_not_exists(
        self, mock_run: MagicMock
    ) -> None:
        """Test check_if_image_exists_locally when image does not exist."""
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(build.check_if_image_exists_locally("tag"))

    @patch("builtins.print")
    @patch("subprocess.run")
    def test_build_image(self, mock_run: MagicMock, mock_print: MagicMock) -> None:
        """Test build_image command construction."""
        mock_run.return_value = MagicMock(returncode=0, stdout="out", stderr="err")
        build.build_image(
            "tag", "Dockerfile", ["ARG1", "val1", "ARG2", "val2"], "context"
        )
        expected_cmd = [
            "docker",
            "buildx",
            "build",
            "--tag",
            "tag",
            "--file",
            "Dockerfile",
            "--build-arg",
            "ARG1=val1",
            "--build-arg",
            "ARG2=val2",
            "context",
        ]
        mock_run.assert_called_once_with(
            expected_cmd, check=True, text=True, capture_output=True
        )
        mock_print.assert_has_calls(
            [
                call("Building image: tag...", file=sys.stderr, end="", flush=True),
                call(" [OK]", file=sys.stderr),
            ]
        )

    @patch("subprocess.run")
    def test_check_if_image_exists_in_remote_registry_exists(
        self, mock_run: MagicMock
    ) -> None:
        """Test check_if_image_exists_in_remote_registry when image exists."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(build.check_if_image_exists_in_remote_registry("tag"))
        mock_run.assert_called_once_with(
            ["docker", "manifest", "inspect", "tag"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_check_if_image_exists_in_remote_registry_not_exists(
        self, mock_run: MagicMock
    ) -> None:
        """Test check_if_image_exists_in_remote_registry when image does not exist."""
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(build.check_if_image_exists_in_remote_registry("tag"))
        mock_run.assert_called_once_with(
            ["docker", "manifest", "inspect", "tag"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("builtins.print")
    @patch("subprocess.run")
    def test_pull_image_from_registry(
        self, mock_run: MagicMock, mock_print: MagicMock
    ) -> None:
        """Test pull_image_from_registry."""
        mock_run.return_value = MagicMock(returncode=0, stdout="out", stderr="err")
        build.pull_image_from_registry("tag")
        mock_run.assert_called_once_with(
            ["docker", "pull", "tag"], check=True, text=True, capture_output=True
        )
        mock_print.assert_has_calls(
            [
                call("Pulling image: tag...", file=sys.stderr, end="", flush=True),
                call(" [OK]", file=sys.stderr),
            ]
        )

    @patch("builtins.print")
    @patch("subprocess.run")
    def test_push_image_to_registry_success(
        self, mock_run: MagicMock, mock_print: MagicMock
    ) -> None:
        """Test push_image_to_registry on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="out", stderr="err")
        build.push_image_to_registry("tag")
        mock_run.assert_called_once_with(
            ["docker", "push", "tag"],
            check=False,
            text=True,
            capture_output=True,
        )
        mock_print.assert_has_calls(
            [
                call("Pushing image: tag...", file=sys.stderr, end="", flush=True),
                call(" [OK]", file=sys.stderr),
            ]
        )

    @patch("builtins.print")
    @patch("subprocess.run")
    def test_push_image_to_registry_failure(
        self, mock_run: MagicMock, mock_print: MagicMock
    ) -> None:
        """Test push_image_to_registry on failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="err")
        build.push_image_to_registry("tag")
        mock_print.assert_has_calls(
            [
                call("Pushing image: tag...", file=sys.stderr, end="", flush=True),
                call(" [FAILED]", file=sys.stderr),
            ]
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
