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
"""Test cases for the bootstrap script"""
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure the bootstrap module can be imported.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bootstrap


# Helper function for mocking sys.exit to capture exit code
def _raise_system_exit_with_arg(*args: object) -> None:
    """Helper side_effect for sys.exit mock to raise SystemExit with the provided code."""
    raise SystemExit(*args)


class TestCopyAndTemplate(unittest.TestCase):
    """A class for testing the copy_and_template function"""

    def setUp(self) -> None:
        """Set up temporary directories for testing."""
        self.src_dir = Path(tempfile.mkdtemp())
        self.dest_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """Clean up temporary directories."""
        shutil.rmtree(str(self.src_dir))
        shutil.rmtree(str(self.dest_dir))

    def test_skips_include_files(self) -> None:
        """Tests that files ending with .include are skipped."""
        # Create a regular file and an include file
        (self.src_dir / "a.txt").open("w").write("content")
        (self.src_dir / "b.txt.include").open("w").write("include content")

        # Run the function
        errors = bootstrap.copy_and_template(self.src_dir, self.dest_dir, {})

        # Check that the regular file was copied and the include file was not
        self.assertFalse(errors)
        self.assertTrue((self.dest_dir / "a.txt").exists())
        self.assertFalse((self.dest_dir / "b.txt.include").exists())


class TestBootstrapScript(unittest.TestCase):
    """A class for testing the bootstrap script"""

    @patch("bootstrap.copy_and_template")
    @patch("os.getcwd")
    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["bootstrap.py", "--template", "cpp"])
    def test_main_success(
        self,
        mock_print: MagicMock,
        mock_sys_exit: MagicMock,
        mock_getcwd: MagicMock,
        mock_copy_and_template: MagicMock,
    ) -> None:
        """Tests the successful execution of the bootstrap script."""
        mock_getcwd.return_value = "/path/to/dest"
        mock_copy_and_template.return_value = False  # No errors

        bootstrap.main()

        script_dir = Path(__file__).parent
        expected_template_dir = (script_dir.parent / "templates" / "cpp").resolve(
            strict=True
        )
        mock_copy_and_template.assert_called_once_with(
            expected_template_dir, Path("/path/to/dest"), {}
        )
        mock_print.assert_called_once_with("Project bootstrapped with 'cpp' template.")
        mock_sys_exit.assert_not_called()

    @patch("sys.exit")
    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("sys.argv", ["bootstrap.py"])
    def test_main_no_template_arg(
        self, mock_stderr: io.StringIO, mock_sys_exit: MagicMock
    ) -> None:
        """Tests that the script exits if no template argument is provided."""
        mock_sys_exit.side_effect = _raise_system_exit_with_arg

        with self.assertRaises(SystemExit) as cm:
            bootstrap.main()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn(
            "the following arguments are required: --template",
            mock_stderr.getvalue(),
        )
        mock_sys_exit.assert_called_once_with(2)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["bootstrap.py", "--template", "cpp", "--args", "foo"])
    def test_main_invalid_context(
        self, mock_print: MagicMock, mock_sys_exit: MagicMock
    ) -> None:
        """Tests that the script exits if no template argument is provided."""
        mock_sys_exit.side_effect = _raise_system_exit_with_arg

        with self.assertRaises(SystemExit) as cm:
            bootstrap.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with(
            "Invalid argument: foo. Expected key=value.", file=sys.stderr
        )
        mock_sys_exit.assert_called_once_with(1)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["bootstrap.py", "--template", "nonexistent"])
    def test_main_template_not_found(
        self, mock_print: MagicMock, mock_sys_exit: MagicMock
    ) -> None:
        """Tests that the script exits if the template directory does not exist."""
        mock_sys_exit.side_effect = _raise_system_exit_with_arg

        with self.assertRaises(SystemExit) as cm:
            bootstrap.main()

        self.assertEqual(cm.exception.code, 1)
        script_dir = Path(__file__).parent
        expected_template_dir = (script_dir.parent / "templates").resolve(
            strict=True
        ) / "nonexistent"
        mock_print.assert_called_once_with(
            f"Template 'nonexistent' not found at '{expected_template_dir}'",
            file=sys.stderr,
        )
        mock_sys_exit.assert_called_once_with(1)

    @patch("bootstrap.copy_and_template", side_effect=Exception("Copy failed"))
    @patch("os.getcwd")
    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["bootstrap.py", "--template", "cpp"])
    def test_main_copy_error(
        self,
        mock_print: MagicMock,
        mock_sys_exit: MagicMock,
        mock_getcwd: MagicMock,
        _: MagicMock,
    ) -> None:
        """Tests that the script handles exceptions during copytree."""
        mock_getcwd.return_value = "/path/to/dest"
        mock_sys_exit.side_effect = _raise_system_exit_with_arg

        with self.assertRaises(SystemExit) as cm:
            bootstrap.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with(
            "An error occurred: Copy failed", file=sys.stderr
        )
        mock_sys_exit.assert_called_once_with(1)

    @patch("bootstrap.copy_and_template")
    @patch("os.getcwd")
    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["bootstrap.py", "--template", "cpp"])
    def test_main_templating_error(
        self,
        mock_print: MagicMock,
        mock_sys_exit: MagicMock,
        mock_getcwd: MagicMock,
        mock_copy_and_template: MagicMock,
    ) -> None:
        """Tests that the script exits if there are templating errors."""
        mock_getcwd.return_value = "/path/to/dest"
        mock_copy_and_template.return_value = True  # Errors occurred
        mock_sys_exit.side_effect = _raise_system_exit_with_arg

        with self.assertRaises(SystemExit) as cm:
            bootstrap.main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with(
            "Errors occurred during templating.", file=sys.stderr
        )
        mock_sys_exit.assert_called_once_with(1)

    @patch("bootstrap.copy_and_template")
    @patch("os.getcwd")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_main_with_templates_root(
        self,
        mock_print: MagicMock,
        mock_sys_exit: MagicMock,
        mock_getcwd: MagicMock,
        mock_copy_and_template: MagicMock,
    ) -> None:
        """Tests the successful execution with a custom templates root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_root = Path(tmpdir)
            (templates_root / "cpp").mkdir()
            sys.argv = [
                "bootstrap.py",
                "--template",
                "cpp",
                "--templates-root",
                str(templates_root),
            ]
            mock_getcwd.return_value = "/path/to/dest"
            mock_copy_and_template.return_value = False  # No errors

            bootstrap.main()

            expected_template_dir = (templates_root / "cpp").resolve(strict=True)
            mock_copy_and_template.assert_called_once_with(
                expected_template_dir, Path("/path/to/dest"), {}
            )
            mock_print.assert_called_once_with(
                "Project bootstrapped with 'cpp' template."
            )
            mock_sys_exit.assert_not_called()

    @patch("bootstrap.copy_and_template")
    @patch("os.getcwd")
    @patch("sys.exit")
    @patch("builtins.print")
    def test_main_with_output_dir(
        self,
        mock_print: MagicMock,
        mock_sys_exit: MagicMock,
        mock_getcwd: MagicMock,
        mock_copy_and_template: MagicMock,
    ) -> None:
        """Tests the successful execution with a custom output directory."""
        sys.argv = [
            "bootstrap.py",
            "--template",
            "cpp",
            "--output-dir",
            "/custom/output/dir",
        ]
        mock_getcwd.return_value = "/path/to/cwd"  # Should be ignored for dest_dir
        mock_copy_and_template.return_value = False  # No errors

        bootstrap.main()

        script_dir = Path(__file__).parent
        expected_template_dir = (script_dir.parent / "templates" / "cpp").resolve(
            strict=True
        )
        mock_copy_and_template.assert_called_once_with(
            expected_template_dir, Path("/custom/output/dir"), {}
        )
        mock_print.assert_called_once_with("Project bootstrapped with 'cpp' template.")
        mock_sys_exit.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
