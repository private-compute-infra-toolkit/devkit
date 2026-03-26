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
"""Test cases for the docker_run script."""

import json
import os
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, mock_open

from scripts import docker_run

IMAGES_DIR = Path(docker_run.__file__).resolve().parent.parent / "images"


class TestDockerRun(unittest.TestCase):
    """Tests for docker_run script."""

    def setUp(self) -> None:
        self.patches: list[Any] = []

        def start_patch(target: str, **kwargs: Any) -> Any:
            patcher = patch(target, **kwargs)
            self.patches.append(patcher)
            return patcher.start()

        self.mock_env = {
            "HOME": "/home/testuser",
            "USER": "testuser",
            "TERM": "xterm-256color",
        }
        patcher_env = patch.dict(os.environ, self.mock_env, clear=True)
        self.patches.append(patcher_env)
        patcher_env.start()

        # Path setups
        start_patch("pathlib.Path.home", return_value=Path("/home/testuser"))
        start_patch("pathlib.Path.mkdir")
        start_patch("pathlib.Path.touch")
        self.mock_path_exists = start_patch(
            "pathlib.Path.exists", autospec=True, return_value=False
        )
        start_patch("pathlib.Path.cwd", return_value=Path("/project"))

        # System info setups
        pw_mock = MagicMock()
        pw_mock.pw_name = "testuser"
        start_patch("pwd.getpwuid", return_value=pw_mock)

        gr_mock = MagicMock()
        gr_mock.gr_name = "testgroup"
        start_patch("grp.getgrgid", return_value=gr_mock)

        grnam_mock = MagicMock()
        grnam_mock.gr_gid = 1000
        self.mock_getgrnam = start_patch("grp.getgrnam", return_value=grnam_mock)

        start_patch("os.getuid", return_value=1000)
        start_patch("os.getgid", return_value=1000)
        start_patch("socket.gethostname", return_value="test-hostname")

        # I/O setups
        self.mock_stdin_isatty = start_patch("sys.stdin.isatty", return_value=True)
        self.mock_stdout_isatty = start_patch("sys.stdout.isatty", return_value=True)
        self.mock_open = start_patch("builtins.open", new_callable=mock_open)
        self.mock_logging_config = start_patch("logging.basicConfig")

        # Process / Script logic setups
        self.mock_start_background_cleanup = start_patch(
            "scripts.docker_run.start_background_cleanup",
            return_value=(MagicMock(), MagicMock()),
        )
        self.mock_start_container_event_handler = start_patch(
            "scripts.docker_run.start_container_event_handler",
            return_value=(MagicMock(), MagicMock(), 12345),
        )
        self.mock_find_project_root = start_patch(
            "scripts.docker_run.find_project_root", return_value=Path("/project")
        )
        self.mock_get_minimal_mounts = start_patch(
            "scripts.docker_run.get_minimal_mounts",
            side_effect=lambda _root, mounts: mounts,
        )

        self.mock_run = start_patch("subprocess.run")
        self.mock_run_result = MagicMock()
        self.mock_run_result.returncode = 0
        self.mock_run.return_value = self.mock_run_result

        self.mock_check_output = start_patch("subprocess.check_output")

    def tearDown(self) -> None:
        for patcher in self.patches:
            patcher.stop()

    def test_main_success(self) -> None:
        """Test main function with minimal successful path."""
        # Git discovery fails, but docker run succeeds
        self.mock_run.side_effect = [
            FileNotFoundError("git not found"),
            self.mock_run_result,
        ]
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch(
            "sys.argv",
            ["docker_run.py", "--devkit-log-file", "/tmp/log", "image:latest", "cmd"],
        ):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        self.mock_logging_config.assert_called_once()
        self.assertEqual(
            self.mock_logging_config.call_args[1]["filename"], Path("/tmp/log")
        )

        # subprocess.run was called for docker run
        docker_call_args = self.mock_run.call_args_list[-1][0][0]
        self.assertEqual(docker_call_args[0], "docker")
        self.assertEqual(docker_call_args[1], "run")
        self.assertIn("--rm", docker_call_args)
        # ... other assertions on docker_call_args ...
        self.assertIn("--volume=/project:/project", docker_call_args)
        self.assertIn("--workdir=/project", docker_call_args)
        self.assertIn("--env=HOME=/home/testuser", docker_call_args)
        self.assertIn("--env=DEVKIT_SOCKET_PORT=12345", docker_call_args)
        self.assertIn("--env=GOOGLE_CLOUD_PROJECT", docker_call_args)
        self.assertIn("--env=GEMINI_API_KEY", docker_call_args)
        self.assertIn("--env=AWS_SECRET_ACCESS_KEY", docker_call_args)
        self.assertIn("--env=AWS_ACCESS_KEY_ID", docker_call_args)
        self.assertIn("--env=AWS_SESSION_TOKEN", docker_call_args)
        self.assertIn("--env=GH_TOKEN", docker_call_args)
        self.assertIn("--env=USER=testuser", docker_call_args)
        self.assertIn("--env=USER_ID=1000", docker_call_args)
        self.assertIn("--env=GROUP=testgroup", docker_call_args)
        self.assertIn("--env=GROUP_ID=1000", docker_call_args)
        self.assertIn("--env=TMPDIR=/tmp", docker_call_args)
        self.assertIn("--env=TERM=xterm-256color", docker_call_args)
        self.assertIn("--env=COLORTERM", docker_call_args)
        self.assertIn("--env=DOCKER_GROUP=docker", docker_call_args)
        self.assertIn("--env=DOCKER_GROUP_ID=1000", docker_call_args)
        self.assertIn("--env=NOBODY_GROUP=nobody", docker_call_args)
        self.assertIn(
            "--env=DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket",
            docker_call_args,
        )
        self.assertIn(
            "--env=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus",
            docker_call_args,
        )
        self.assertIn("--env=ADDITIONAL_PATH=", docker_call_args)
        self.assertIn("--net=host", docker_call_args)
        self.assertIn("--ipc=host", docker_call_args)
        self.assertIn("--hostname=test-hostname", docker_call_args)
        self.assertIn("--volume=/tmp:/tmp", docker_call_args)
        self.assertTrue(
            any(arg.startswith("--entrypoint=") for arg in docker_call_args)
        )
        self.assertIn("--tty", docker_call_args)
        self.assertIn("--interactive", docker_call_args)
        self.assertIn("image:latest", docker_call_args)
        self.assertIn("cmd", docker_call_args)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_find_root_fails(self) -> None:
        """Test main exits when project root is not found."""
        self.mock_find_project_root.side_effect = FileNotFoundError("Not found")

        with patch("sys.argv", ["docker_run.py"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 1)

    def test_main_find_root_success(self) -> None:
        """Test main function when find_project_root is called."""
        with patch("sys.argv", ["docker_run.py", "image:latest"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        self.mock_find_project_root.assert_called_once()
        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_groups_not_found(self) -> None:
        """Test main function when docker/nobody groups are not found."""
        # First call (git check) fails, second call (docker run) succeeds
        self.mock_run.side_effect = [
            FileNotFoundError("git not found"),
            self.mock_run_result,
        ]
        self.mock_getgrnam.side_effect = KeyError("group not found")
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch("sys.argv", ["docker_run.py", "image:latest"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        docker_call_args = self.mock_run.call_args_list[-1][0][0]
        self.assertIn("--env=DOCKER_GROUP_ID=0", docker_call_args)
        self.assertNotIn("--env=NOBODY_GROUP_ID=0", docker_call_args)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_complex(self) -> None:
        """Test main function with complex branches."""
        self.mock_stdin_isatty.return_value = False
        self.mock_stdout_isatty.return_value = False
        self.mock_path_exists.side_effect = lambda path: str(path).endswith(
            "devkit.json"
        )

        self.mock_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps({"docker": {"run": ["--env=DEVKIT_JSON_ARG=1"]}})
        )

        # Git Success (two calls)
        git_check_result = MagicMock()
        git_check_result.returncode = 0
        git_check_result.stdout = "true"
        self.mock_run.side_effect = [git_check_result, self.mock_run_result]
        self.mock_check_output.return_value = "/other/git/dir"

        os.environ["DEVKIT_DOCKER_RUN_ARGS"] = "--env=ENV_ARG=1"
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch("sys.argv", ["docker_run.py", "img"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        docker_call_args = self.mock_run.call_args_list[-1][0][0]
        self.assertIn("--env=GIT_DISCOVERY_ACROSS_FILESYSTEM=1", docker_call_args)
        self.assertIn("--env=DEVKIT_JSON_ARG=1", docker_call_args)
        self.assertIn("--env=ENV_ARG=1", docker_call_args)
        self.assertIn("--interactive", docker_call_args)
        self.assertNotIn("--tty", docker_call_args)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_no_tty(self) -> None:
        """Test main function when not in a TTY."""
        self.mock_stdin_isatty.return_value = False
        self.mock_stdout_isatty.return_value = False
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch("sys.argv", ["docker_run.py", "image:latest"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        docker_call_args = self.mock_run.call_args_list[-1][0][0]
        self.assertIn("--interactive", docker_call_args)
        self.assertNotIn("--tty", docker_call_args)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_devkit_json_exception(self) -> None:
        """Test main function when devkit.json raises an exception."""
        self.mock_path_exists.side_effect = lambda path: str(path).endswith(
            "devkit.json"
        )
        self.mock_open.side_effect = Exception("Read error")
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch("sys.argv", ["docker_run.py", "image:latest"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_env_overrides(self) -> None:
        """Test main function respects USER, USER_ID, GROUP, and GROUP_ID overrides."""
        os.environ["USER"] = "overridenuser"
        os.environ["USER_ID"] = "2000"
        os.environ["GROUP"] = "overridengroup"
        os.environ["GROUP_ID"] = "3000"
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch("sys.argv", ["docker_run.py", "image:latest"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 0)

        docker_call_args = self.mock_run.call_args_list[-1][0][0]
        self.assertIn("--env=USER=overridenuser", docker_call_args)
        self.assertIn("--env=USER_ID=2000", docker_call_args)
        self.assertIn("--env=GROUP=overridengroup", docker_call_args)
        self.assertIn("--env=GROUP_ID=3000", docker_call_args)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )

    def test_main_keyboard_interrupt(self) -> None:
        """Test main function handles KeyboardInterrupt."""
        # Git discovery fails, docker run raises KeyboardInterrupt
        self.mock_run.side_effect = [self.mock_run_result, KeyboardInterrupt()]
        os.environ["DEVKIT_HOST_PROJECT_ROOT"] = "/project"

        with patch("sys.argv", ["docker_run.py", "image:latest"]):
            with self.assertRaises(SystemExit) as cm:
                docker_run.main()
            self.assertEqual(cm.exception.code, 130)

        self.mock_start_background_cleanup.assert_called_once_with(
            Path("/project/devkit.json"), [IMAGES_DIR]
        )
        # Get cancel_event and mock_thread from return_value
        mock_thread, mock_cancel_event = self.mock_start_background_cleanup.return_value
        mock_cancel_event.set.assert_called_once()
        mock_thread.join.assert_called_once()

        mock_event_thread, mock_event_cancel, _ = (
            self.mock_start_container_event_handler.return_value
        )
        mock_event_cancel.set.assert_called_once()
        mock_event_thread.join.assert_called_once()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
