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

"""Unit Tests for Generating BEP"""

import subprocess
import sys
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).parent.resolve(strict=True)))
from bep import (
    generate_bazel_events_folder,
    generate_build_event_json,
    main,
    run_command,
)


class TestBepGeneration(unittest.TestCase):
    """
    A test suite for the bep.py script using the unittest framework.
    """

    # Tests for the run_command function
    @patch("bep.subprocess.run")
    def test_run_command_success(self, mock_subprocess_run: MagicMock) -> None:
        """
        Tests that `run_command` correctly calls `subprocess.run`
        and returns nothing when capture_output=False.
        """
        cmd = ["echo", "hello"]
        result = run_command(cmd)

        mock_subprocess_run.assert_called_once_with(
            cmd,
            check=True,
            text=True,
            capture_output=False,
            encoding="utf-8",
        )
        self.assertEqual(result, "")

    @patch("bep.subprocess.run")
    def test_run_command_capture_output_success(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        """
        Tests that `run_command` returns stdout when capture_output=True.
        """
        # Configure the mock to simulate a process with stdout
        mock_process_result = MagicMock()
        mock_process_result.stdout = "some output\n"
        mock_subprocess_run.return_value = mock_process_result

        cmd = ["ls", "-l"]
        output = run_command(cmd, capture_output=True)

        mock_subprocess_run.assert_called_once_with(
            cmd, check=True, text=True, capture_output=True, encoding="utf-8"
        )
        self.assertEqual(output, "some output")

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("bep.subprocess.run")
    def test_run_command_called_process_error(
        self, mock_subprocess_run: MagicMock, mock_stderr: MagicMock
    ) -> None:
        """
        Tests that `run_command` catches CalledProcessError,
        prints an error, and exits.
        """
        cmd = ["false"]
        error = subprocess.CalledProcessError(
            returncode=1, cmd=cmd, stderr="error details"
        )
        mock_subprocess_run.side_effect = error

        with self.assertRaises(SystemExit) as cm:
            run_command(cmd)

        # Check that the exit code is 1
        self.assertEqual(cm.exception.code, 1)

        # Check that the correct message was printed to stderr
        stderr_output = mock_stderr.getvalue()
        self.assertIn(
            f"Error: Command '{' '.join(cmd)}' failed with exit code 1.", stderr_output
        )
        self.assertIn("STDERR:\nerror details", stderr_output)

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("bep.subprocess.run")
    def test_run_command_file_not_found_error(
        self, mock_subprocess_run: MagicMock, mock_stderr: MagicMock
    ) -> None:
        """
        Tests that `run_command` catches FileNotFoundError
        and exits with the correct message.
        """
        cmd = ["non_existent_command"]
        mock_subprocess_run.side_effect = FileNotFoundError

        with self.assertRaises(SystemExit) as cm:
            run_command(cmd)

        self.assertEqual(cm.exception.code, 1)
        self.assertIn(f"Error: Command not found: {cmd[0]}", mock_stderr.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("bep.subprocess.run")
    def test_run_command_called_process_error_with_stdout_and_stderr(
        self, mock_subprocess_run: MagicMock, mock_stderr: MagicMock
    ) -> None:
        """
        Tests that run_command prints both stdout and stderr when a
        CalledProcessError with both attributes is raised.
        """
        cmd = ["failing_script"]

        # Exception with both stdout and stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            output="Some diagnostic output on stdout.",
            stderr="Critical error message on stderr.",
        )
        mock_subprocess_run.side_effect = error

        with self.assertRaises(SystemExit):
            run_command(cmd)

        stderr_output = mock_stderr.getvalue()

        self.assertIn(
            f"Error: Command '{' '.join(cmd)}' failed with exit code 1.", stderr_output
        )

        self.assertIn("STDOUT:\nSome diagnostic output on stdout.", stderr_output)
        self.assertIn("STDERR:\nCritical error message on stderr.", stderr_output)

    # Tests for the generate_build_event_json function
    @patch("bep.tempfile.TemporaryDirectory")
    @patch("bep.run_command")
    def test_generate_build_event_json_for_fetch(
        self, mock_run_command: MagicMock, mock_tempdir: MagicMock
    ) -> None:
        """
        Tests that `generate_build_event_json` builds the correct
        command for `bazel fetch`.
        """
        mock_tempdir.return_value.__enter__.side_effect = [
            "/tmp/bazel_cache",
            "/tmp/bazel_registry_cache",
        ]

        target = "//my:target"
        output_path = Path("/tmp/bep.json")

        generate_build_event_json(target, output_path, "fetch")

        expected_cmd = [
            "bazel",
            "--output_base=/tmp/bazel_cache",
            "fetch",
            f"--build_event_json_file={output_path}",
            "--repository_cache=/tmp/bazel_registry_cache",
            target,
        ]
        mock_run_command.assert_called_once_with(expected_cmd)

    @patch("bep.tempfile.TemporaryDirectory")
    @patch("bep.run_command")
    def test_generate_build_event_json_for_build(
        self, mock_run_command: MagicMock, mock_tempdir: MagicMock
    ) -> None:
        """
        Tests that `generate_build_event_json` adds the
        `--noremote_accept_cached` flag for the `bazel build` command.
        """
        mock_tempdir.return_value.__enter__.side_effect = [
            "/tmp/bazel_cache",
            "/tmp/bazel_registry_cache",
        ]
        target = "//my:target"
        output_path = Path("/tmp/bep.json")

        generate_build_event_json(target, output_path, "build")

        expected_cmd = [
            "bazel",
            "--output_base=/tmp/bazel_cache",
            "build",
            f"--build_event_json_file={output_path}",
            "--repository_cache=/tmp/bazel_registry_cache",
            target,
            "--noremote_accept_cached",
        ]
        mock_run_command.assert_called_once_with(expected_cmd)

    # Tests for the generate_bazel_events_folder function
    @patch("pathlib.Path.mkdir")
    @patch("bep.generate_build_event_json")
    def test_generate_bazel_events_folder(
        self, mock_generate_json: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """
        Tests that `generate_bazel_events_folder` iterates over targets,
        creates a directory, and calls `generate_build_event_json` correctly.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            targets = ["//services/api:foo", "//common:bar"]
            command = "build"

            generate_bazel_events_folder(targets, command, output_dir)

            # Check that an attempt was made to create the correct directory
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)
            # Check if `mkdir` was called once for each target + one for parent dir
            self.assertEqual(mock_mkdir.call_count, 3)

            # Check if `generate_build_event_json` was called for each target
            self.assertEqual(mock_generate_json.call_count, 2)

            # Verify the calls for each target, including the sanitized filename
            expected_calls = [
                call(
                    "//services/api:foo", output_dir / "api_foo" / "bep.json", command
                ),
                call("//common:bar", output_dir / "common_bar" / "bep.json", command),
            ]
            mock_generate_json.assert_has_calls(expected_calls, any_order=True)

    @patch("pathlib.Path.mkdir")
    @patch("bep.generate_build_event_json")
    def test_generate_bazel_events_folder_all_targets(
        self, mock_generate_json: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Tests filename sanitization for the empty target list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            targets: list[str] = []
            command = "fetch"
            generate_bazel_events_folder(targets, command, output_dir)

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            expected_output_file = output_dir / "bep.json"
            mock_generate_json.assert_called_once_with(
                "//...", expected_output_file, command
            )

    # Tests for the main function
    @patch("bep.generate_bazel_events_folder")
    def test_main_with_args(self, mock_generate_folder: MagicMock) -> None:
        """
        Tests that `main` correctly parses arguments and calls
        `generate_bazel_events_folder`.
        """
        targets = ["//target1", "//target2"]
        command = "build"
        test_args = ["bep.py", "--targets"] + targets + ["--command", command]

        with patch.object(sys, "argv", test_args):
            main()

        mock_generate_folder.assert_called_once_with(
            targets, command, Path("bazel-bep")
        )

    @patch("bep.generate_bazel_events_folder")
    def test_main_with_default_command(self, mock_generate_folder: MagicMock) -> None:
        """
        Tests that `main` uses the default 'fetch' command
        when none is provided.
        """
        targets = ["//target1"]
        test_args = ["bep.py", "--targets"] + targets

        with patch.object(sys, "argv", test_args):
            main()

        mock_generate_folder.assert_called_once_with(
            targets, "fetch", Path("bazel-bep")
        )

    @patch("bep.generate_bazel_events_folder")
    def test_main_with_default_args(self, mock_generate_folder: MagicMock) -> None:
        """
        Tests that `main` uses default arguments when none are provided.
        """
        test_args = ["bep.py"]

        with patch.object(sys, "argv", test_args):
            main()

        mock_generate_folder.assert_called_once_with([], "fetch", Path("bazel-bep"))

    @patch("bep.generate_bazel_events_folder")
    def test_main_with_custom_output_dir(self, mock_generate_folder: MagicMock) -> None:
        """
        Tests that `main` correctly passes a custom output directory.
        """
        targets = ["//target1"]
        output_dir = "custom/logs"
        test_args = ["bep.py", "--targets", *targets, "--output_dir", output_dir]

        with patch.object(sys, "argv", test_args):
            main()

        mock_generate_folder.assert_called_once_with(targets, "fetch", Path(output_dir))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
