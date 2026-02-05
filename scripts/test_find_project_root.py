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
"""Test cases for the find_project_root script."""

import os
import shutil
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import find_project_root


class TestFindProjectRoot(unittest.TestCase):
    """Tests for find_project_root script."""

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()

    def tearDown(self) -> None:
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_finds_root_in_current_dir(self) -> None:
        """Test finding root when 'devkit' is in the current directory."""
        (self.test_dir / "devkit").touch()
        os.chdir(self.test_dir)

        with patch("os.getenv", return_value=str(self.test_dir)):
            result = find_project_root.find_project_root()
        self.assertEqual(result, self.test_dir)

    def test_finds_root_from_subdir(self) -> None:
        """Test finding root from a subdirectory."""
        (self.test_dir / "devkit").touch()
        subdir = self.test_dir / "subdir" / "deep"
        subdir.mkdir(parents=True)
        os.chdir(subdir)

        with patch("os.getenv", return_value=str(subdir)):
            result = find_project_root.find_project_root()

        self.assertEqual(result, self.test_dir)

    def test_fails_when_not_found(self) -> None:
        """Test failure when 'devkit' is not in the tree."""
        os.chdir(self.test_dir)
        with patch("os.getenv", return_value=str(self.test_dir)):
            with self.assertRaises(FileNotFoundError):
                find_project_root.find_project_root()

    def test_fallback_to_cwd_when_pwd_missing(self) -> None:
        """Test fallback to Path.cwd() when PWD is not set."""
        (self.test_dir / "devkit").touch()
        os.chdir(self.test_dir)

        def getenv_side_effect(_: str, default: str | None = None) -> str | None:
            return default

        with patch("os.getenv", side_effect=getenv_side_effect):
            result = find_project_root.find_project_root()

        self.assertEqual(result, self.test_dir)


class TestFindProjectRootMain(unittest.TestCase):
    """Tests for the main function in find_project_root."""

    @patch("sys.stdout", new_callable=StringIO)
    @patch("scripts.find_project_root.find_project_root")
    def test_main_success(
        self, mock_find_project_root: MagicMock, mock_stdout: MagicMock
    ) -> None:
        """Test main prints the root path when found."""
        expected_path = Path("/path/to/project")
        mock_find_project_root.return_value = expected_path

        with patch("sys.argv", ["find_project_root.py"]):
            find_project_root.main()

        self.assertEqual(mock_stdout.getvalue().strip(), str(expected_path))

    @patch("sys.stderr", new_callable=StringIO)
    @patch("scripts.find_project_root.find_project_root")
    def test_main_failure(
        self, mock_find_project_root: MagicMock, mock_stderr: MagicMock
    ) -> None:
        """Test main exits with error when root is not found."""
        mock_find_project_root.side_effect = FileNotFoundError("Not found")

        with patch("sys.argv", ["find_project_root.py"]):
            with self.assertRaises(SystemExit) as cm:
                find_project_root.main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Not found", mock_stderr.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
