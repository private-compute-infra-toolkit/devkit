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
from typing import Any, Dict, List
from unittest.mock import MagicMock, call, mock_open, patch
import graphlib

# Ensure the package root is in the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from devkit.docker import build


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

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"docker": {"registry": "my-repo"}}',
    )
    def test_load_config_success(
        self, unused_mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test load_config successfully loads registry."""
        build.load_config("dummy/path/devkit.json")
        self.assertEqual(build.REPO, "my-repo")
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
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("builtins.print")
    def test_load_config_json_decode_error(
        self,
        mock_print: MagicMock,
        unused_mock_file: MagicMock,
        unused_mock_exists: MagicMock,
    ) -> None:
        """Test load_config with JSON decode error."""
        with self.assertRaises(SysExitCalled):
            build.load_config("dummy/path/devkit.json")
        self.mock_sys_exit.assert_called_once_with(1)
        mock_print.assert_called_with(
            "Error: Could not decode dummy/path/devkit.json: "
            "Expecting value: line 1 column 1 (char 0)"
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
    @patch("builtins.print")
    def test_load_image_configs_not_a_dict(
        self,
        mock_print: MagicMock,
        unused_mock_file: MagicMock,
        unused_mock_exists: MagicMock,
        mock_join: MagicMock,
    ) -> None:
        """Test load_image_configs with non-dict JSON content."""
        mock_join.return_value = "search/path/deps.json"
        configs = build.load_image_configs(["search/path"])
        self.assertEqual(configs, {})
        mock_print.assert_any_call(
            "Warning: search/path/deps.json does not contain a dict of configs."
        )

    @patch("os.path.join")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("builtins.print")
    def test_load_image_configs_json_decode_error(
        self,
        mock_print: MagicMock,
        unused_mock_file: MagicMock,
        unused_mock_exists: MagicMock,
        mock_join: MagicMock,
    ) -> None:
        """Test load_image_configs with JSON decode error."""
        mock_join.return_value = "search/path/deps.json"
        with self.assertRaises(SysExitCalled):
            build.load_image_configs(["search/path"])
        self.mock_sys_exit.assert_called_once_with(1)
        mock_print.assert_any_call(
            "Error: Could not decode search/path/deps.json: "
            "Expecting value: line 1 column 1 (char 0)"
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

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_manage_docker_image_exists_locally(
        self, mock_print: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test manage_docker_image when image exists locally."""
        mock_run.return_value = MagicMock(returncode=0)
        build.manage_docker_image("tag", "Dockerfile", [], "context")
        mock_run.assert_called_once_with(
            ["docker", "image", "inspect", "tag"],
            capture_output=True,
            text=True,
            check=False,
        )
        mock_print.assert_any_call(
            "Image tag already exists locally. Skipping build/pull."
        )

    @patch("subprocess.run")
    def test_manage_docker_image_exists_remotely(self, mock_run: MagicMock) -> None:
        """Test manage_docker_image when image exists remotely."""
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="pulled", stderr="pull warning"),
        ]
        build.manage_docker_image("tag", "Dockerfile", [], "context")
        self.assertEqual(mock_run.call_count, 3)

    @patch("subprocess.run")
    def test_manage_docker_image_build_and_push_success(
        self, mock_run: MagicMock
    ) -> None:
        """Test manage_docker_image builds and pushes successfully."""
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=1),
            MagicMock(returncode=0, stdout="built", stderr="build warning"),
            MagicMock(returncode=0, stdout="pushed", stderr="push warning"),
        ]
        build.manage_docker_image("tag", "Dockerfile", ["ARG", "val"], "context")
        self.assertEqual(mock_run.call_count, 4)

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_manage_docker_image_build_and_push_fail(
        self, mock_print: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test manage_docker_image builds and push fails."""
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=1),
            MagicMock(returncode=0, stdout="built", stderr=""),
            MagicMock(returncode=1, stderr="push failed"),
        ]
        build.manage_docker_image("tag", "Dockerfile", [], "context")
        self.assertEqual(mock_run.call_count, 4)
        mock_print.assert_any_call(
            "Warning: Failed to push image tag. Continuing with local image."
        )

    @patch("subprocess.run")
    def test_manage_docker_image_called_process_error(
        self, mock_run: MagicMock
    ) -> None:
        """Test manage_docker_image with CalledProcessError."""
        error = subprocess.CalledProcessError(1, "cmd")
        error.stdout = "out"
        error.stderr = "err"
        mock_run.side_effect = error
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context")
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(0, "cmd"))
    def test_manage_docker_image_called_process_error_zero_exit(
        self, unused_mock_run: MagicMock
    ) -> None:
        """Test manage_docker_image with CalledProcessError with exit code 0."""
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context")
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_manage_docker_image_file_not_found_error(
        self, unused_mock_run: MagicMock
    ) -> None:
        """Test manage_docker_image with FileNotFoundError."""
        with self.assertRaises(SysExitCalled):
            build.manage_docker_image("tag", "Dockerfile", [], "context")
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=False)
    def test_process_image_dockerfile_not_found(
        self, unused_mock_exists: MagicMock
    ) -> None:
        """Test process_image when Dockerfile is not found."""
        with self.assertRaises(SysExitCalled):
            build.process_image("image", {}, {}, False, None, ["search/path"])
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    def test_process_image_dependency_not_found(
        self, unused_mock_realpath: MagicMock, unused_mock_exists: MagicMock
    ) -> None:
        """Test process_image when a dependency tag is not found."""
        with self.assertRaises(SysExitCalled):
            build.process_image(
                "image", {"DEP": "dep-image"}, {}, False, None, ["search/path"]
            )
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    @patch("devkit.docker.build.calculate_sha256", side_effect=FileNotFoundError)
    def test_process_image_calculate_sha_file_not_found(
        self,
        unused_mock_sha: MagicMock,
        unused_mock_realpath: MagicMock,
        unused_mock_exists: MagicMock,
    ) -> None:
        """Test process_image with FileNotFoundError during SHA calculation."""
        with self.assertRaises(SysExitCalled):
            build.process_image("image", {}, {}, False, None, ["search/path"])
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    @patch("devkit.docker.build.calculate_sha256", return_value="sha123")
    @patch("devkit.docker.build.get_image_tag", return_value="tag123")
    @patch("devkit.docker.build.manage_docker_image")
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
            "image", dependencies, generated_tags, False, None, ["search/path"]
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
        )

    @patch("os.path.exists", return_value=True)
    @patch("os.path.realpath", return_value="/abs/path/to/Dockerfile")
    @patch("devkit.docker.build.calculate_sha256", return_value="sha123")
    @patch("devkit.docker.build.get_image_tag", return_value="tag123")
    @patch("devkit.docker.build.manage_docker_image")
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
            build.process_image("image", {}, {}, True, "image", ["search/path"])
        self.mock_sys_exit.assert_called_once_with(0)

    def test_get_dependency_subgraph_target_not_in_map(self) -> None:
        """Test get_dependency_subgraph when target is not in the config map."""
        result = build.get_dependency_subgraph("target", {})
        self.assertEqual(result, [])

    def test_get_dependency_subgraph_success(self) -> None:
        """Test get_dependency_subgraph for a valid graph."""
        image_configs_map: Dict[str, build.ImageConfig] = {
            "a": {"deps": {"FROM": "b"}},
            "b": {"deps": {"FROM": "c"}},
            "c": {"deps": {}},
            "d": {"deps": {}},
        }
        result = build.get_dependency_subgraph("a", image_configs_map)
        self.assertEqual(result, ["c", "b", "a"])

    def test_get_dependency_subgraph_cycle(self) -> None:
        """Test get_dependency_subgraph with a cycle."""
        image_configs_map: Dict[str, build.ImageConfig] = {
            "a": {"deps": {"FROM": "b"}},
            "b": {"deps": {"FROM": "a"}},
        }
        with self.assertRaises(SysExitCalled):
            build.get_dependency_subgraph("a", image_configs_map)
        self.mock_sys_exit.assert_called_once_with(1)

    @patch("argparse.ArgumentParser")
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
    @patch("devkit.docker.build.get_dependency_subgraph")
    @patch("devkit.docker.build.process_image")
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
        )
        mock_argparse.return_value.parse_args.return_value = args
        image_configs: build.ImageConfigsMap = {
            "a": {"deps": {}},
            "b": {"deps": {}},
        }
        mock_load_images.return_value = image_configs
        mock_subgraph.return_value = ["a"]
        build.main()
        mock_load_images.assert_called_once_with(["path"])
        mock_subgraph.assert_called_once_with("a", image_configs)
        mock_process.assert_called_once_with("a", {}, {}, False, None, ["path"])

    @patch("argparse.ArgumentParser")
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
    @patch("graphlib.TopologicalSorter")
    @patch("devkit.docker.build.process_image")
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
        )
        mock_argparse.return_value.parse_args.return_value = args
        image_configs: build.ImageConfigsMap = {
            "a": {"deps": {"FROM": "b"}},
            "b": {"deps": {}},
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
        ) -> str:
            actual_calls.append(
                call(
                    image_name,
                    dependencies.copy(),
                    gen_tags.copy(),
                    print_tag_mode,
                    target_image_for_tag_print,
                    search_paths,
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
            call("b", {}, {}, False, None, ["path"]),
            call(
                "a",
                {"FROM": "b"},
                {"b": "tag-for-b"},
                False,
                None,
                ["path"],
            ),
        ]
        self.assertEqual(actual_calls, expected_calls)

    @patch("argparse.ArgumentParser")
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
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
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
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
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
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
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
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
    @patch("devkit.docker.build.load_config")
    @patch("devkit.docker.build.load_image_configs")
    @patch("devkit.docker.build.get_dependency_subgraph")
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
