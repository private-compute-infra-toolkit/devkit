#!/usr/bin/env python3
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test cases for the bootstrap script"""
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Dict

# Ensure the bootstrap module can be imported.
sys.path.insert(0, str(Path(__file__).parent.resolve(strict=True)))
import bootstrap


class TestBootstrapTemplating(unittest.TestCase):
    """A class for testing the bootstrap script's templating functionality."""

    def setUp(self) -> None:
        """Set up a temporary directory for testing."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.src_dir = self.test_dir / "src"
        self.dest_dir = self.test_dir / "dest"
        self.src_dir.mkdir(parents=True)
        self.dest_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        """Clean up the temporary directory."""
        shutil.rmtree(str(self.test_dir))

    def test_copy_and_template(self) -> None:
        """Tests that files are correctly templated."""
        template_content = "Hello, {{ name }}!"
        context: Dict[str, str] = {"name": "World"}
        expected_content = "Hello, World!\n"
        # Create a dummy template file
        with (self.src_dir / "test.txt").open("w", encoding="utf-8") as f:
            f.write(template_content)

        bootstrap.copy_and_template(self.src_dir, self.dest_dir, context)

        # Check that the file was created and templated
        dest_file_path = self.dest_dir / "test.txt"
        self.assertTrue(dest_file_path.exists())
        with dest_file_path.open("r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, expected_content)

    @patch("os.getcwd")
    @patch(
        "sys.argv",
        ["bootstrap.py", "--template", "test_template", "--args", "name=World"],
    )
    def test_main_with_templating(self, mock_getcwd: MagicMock) -> None:
        """Tests the main function with templating."""
        mock_getcwd.return_value = str(self.dest_dir)
        template_dir = (
            Path(__file__).parent.resolve(strict=True).parent
            / "templates"
            / "test_template"
        )
        template_content = "Hello, {{ name }}!\n"
        expected_content = "Hello, World!\n"
        template_dir.mkdir(parents=True, exist_ok=True)
        # Create a dummy template file
        with (template_dir / "footest.txt").open("w", encoding="utf-8") as f:
            f.write(template_content)

        bootstrap.main()

        dest_file_path = self.dest_dir / "footest.txt"
        self.assertTrue(dest_file_path.exists())
        with dest_file_path.open("r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, expected_content)

        shutil.rmtree(str(template_dir))

    def test_copy_and_template_with_include(self) -> None:
        """Tests that files can include other files."""
        main_template_content = "This is the main file.\n{% include 'included.txt' %}"
        included_content = "This is the included file."
        expected_content = "This is the main file.\nThis is the included file.\n"
        context: Dict[str, str] = {}

        # Create dummy template files
        with (self.src_dir / "main.txt").open("w", encoding="utf-8") as f:
            f.write(main_template_content)
        with (self.src_dir / "included.txt").open("w", encoding="utf-8") as f:
            f.write(included_content)

        bootstrap.copy_and_template(self.src_dir, self.dest_dir, context)

        # Check that the file was created and templated
        dest_file_path = self.dest_dir / "main.txt"
        self.assertTrue(dest_file_path.exists())
        with dest_file_path.open("r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, expected_content)

    @patch("builtins.print")
    def test_copy_and_template_syntax_error(self, mock_print: MagicMock) -> None:
        """Tests that template syntax errors are handled."""
        template_content = "Hello, {{ name }!"  # Invalid syntax
        context: Dict[str, str] = {"name": "World"}
        src_file_path = self.src_dir / "test.txt"
        with src_file_path.open("w", encoding="utf-8") as f:
            f.write(template_content)

        errors = bootstrap.copy_and_template(self.src_dir, self.dest_dir, context)

        self.assertTrue(errors)
        mock_print.assert_any_call(
            f"Error in template: {src_file_path}", file=sys.stderr
        )

    @patch("builtins.print")
    def test_copy_and_template_undefined_error(self, mock_print: MagicMock) -> None:
        """Tests that undefined variable errors are handled."""
        template_content = "Hello, {{ name }}!"
        context: Dict[str, str] = {}  # Missing 'name'
        src_file_path = self.src_dir / "test.txt"
        with src_file_path.open("w", encoding="utf-8") as f:
            f.write(template_content)

        errors = bootstrap.copy_and_template(self.src_dir, self.dest_dir, context)

        self.assertTrue(errors)
        mock_print.assert_any_call(
            f"Error in template: {src_file_path}", file=sys.stderr
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
