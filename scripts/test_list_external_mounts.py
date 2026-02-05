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
"""
Tests for list_external_mounts.
"""
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import list_external_mounts


class ListExternalMountsTest(unittest.TestCase):
    """
    Tests for list_external_mounts.
    """

    def setUp(self) -> None:
        """
        Set up a temporary directory structure for testing.
        """
        self.test_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.test_dir_obj.name)
        self.scan_dir = self.test_dir / "scan"
        self.external_dir = self.test_dir / "external"
        self.scan_dir.mkdir()
        self.external_dir.mkdir()

    def tearDown(self) -> None:
        """
        Clean up the temporary directory.
        """
        self.test_dir_obj.cleanup()

    def test_root_dir_is_symlink(self) -> None:
        """Test when the root directory itself is a symlink."""
        real_scan_dir = self.test_dir / "real_scan"
        real_scan_dir.mkdir()
        symlink_scan_dir = self.test_dir / "symlink_scan"
        symlink_scan_dir.symlink_to(real_scan_dir)

        result = list_external_mounts.get_minimal_mounts(symlink_scan_dir, [])
        self.assertEqual(result, {real_scan_dir.resolve()})

    def test_symlink_to_external_dir(self) -> None:
        """Test symlink to an external directory is detected."""
        (self.scan_dir / "link_to_external_dir").symlink_to(self.external_dir)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.external_dir.resolve()})

    def test_symlink_to_external_file(self) -> None:
        """Test symlink to an external file reports the file path."""
        external_file = self.external_dir / "file.txt"
        external_file.touch()
        (self.scan_dir / "link_to_external_file").symlink_to(external_file)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {external_file.resolve()})

    def test_nested_symlink(self) -> None:
        """Test a symlink pointing to another symlink is resolved."""
        (self.scan_dir / "link1").symlink_to(self.scan_dir / "link2")
        (self.scan_dir / "link2").symlink_to(self.external_dir)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.external_dir.resolve()})

    def test_symlink_to_parent_of_already_reported_path(self) -> None:
        """Test that only the top-most external path is reported."""
        external_child_dir = self.external_dir / "child"
        external_child_dir.mkdir()
        (self.scan_dir / "link_to_child").symlink_to(external_child_dir)
        (self.scan_dir / "link_to_parent").symlink_to(self.external_dir)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.external_dir.resolve()})

    def test_cyclical_symlink(self) -> None:
        """Test that cyclical symlinks do not cause an infinite loop."""
        (self.scan_dir / "cycle1").symlink_to(self.scan_dir / "cycle2")
        (self.scan_dir / "cycle2").symlink_to(self.scan_dir / "cycle1")
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, set())

    def test_internal_symlink(self) -> None:
        """Test that symlinks pointing inside the scan directory are ignored."""
        internal_dir = self.scan_dir / "internal"
        internal_dir.mkdir()
        (self.scan_dir / "link_to_internal").symlink_to(internal_dir)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, set())

    def test_broken_symlink(self) -> None:
        """Test that broken symlinks are ignored."""
        (self.scan_dir / "broken_link").symlink_to("non_existent_path")
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, set())

    def test_symlink_in_subdirectory(self) -> None:
        """Test that symlinks in subdirectories are found."""
        sub_scan_dir = self.scan_dir / "sub"
        sub_scan_dir.mkdir()
        external_dir2 = self.test_dir / "external2"
        external_dir2.mkdir()
        (sub_scan_dir / "link_in_subdir").symlink_to(external_dir2)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {external_dir2.resolve()})

    def test_symlink_to_file_in_external_dir(self) -> None:
        """Test symlink to a file in an already-reported external directory."""
        (self.scan_dir / "link_to_dir").symlink_to(self.external_dir)
        external_file = self.external_dir / "another_file.txt"
        external_file.touch()
        (self.scan_dir / "link_to_file_in_external_dir").symlink_to(external_file)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.external_dir.resolve()})

    def test_multiple_links_to_same_external_dir(self) -> None:
        """Test multiple links to an external dir and its children."""
        sub_scan_dir1 = self.scan_dir / "sub1"
        sub_scan_dir2 = self.scan_dir / "sub2"
        sub_scan_dir3 = self.scan_dir / "sub3"
        sub_scan_dir1.mkdir()
        sub_scan_dir2.mkdir()
        sub_scan_dir3.mkdir()

        external_child_dir = self.external_dir / "child"
        external_child_dir.mkdir()
        external_child_file = external_child_dir / "file.txt"
        external_child_file.touch()

        (sub_scan_dir1 / "link_to_dir").symlink_to(self.external_dir)
        (sub_scan_dir2 / "link_to_child_dir").symlink_to(external_child_dir)
        (sub_scan_dir3 / "link_to_child_file").symlink_to(external_child_file)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.external_dir.resolve()})

    def test_symlink_to_scan_dir_itself(self) -> None:
        """Test that a symlink to the scan directory itself is ignored."""
        (self.scan_dir / "link_to_self").symlink_to(self.scan_dir)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, set())

    def test_self_referencing_symlink(self) -> None:
        """Test that a self-referencing symlink is handled."""
        link_path = self.scan_dir / "self_link"
        link_path.symlink_to(link_path)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, set())

    def test_symlink_to_parent_of_scan_dir(self) -> None:
        """Test symlink to a parent of the scan directory is detected."""
        (self.scan_dir / "link_to_parent").symlink_to(self.test_dir)
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.test_dir.resolve()})

    def test_multiple_external_roots_with_children(self) -> None:
        """Test with multiple external directories and links to their children."""
        external_dir2 = self.test_dir / "external2"
        external_dir2.mkdir()

        external1_child = self.external_dir / "child"
        external1_child.mkdir()
        external2_child = external_dir2 / "other"
        external2_child.mkdir()

        (self.scan_dir / "link1").symlink_to(self.external_dir)
        (self.scan_dir / "link2").symlink_to(external1_child)
        (self.scan_dir / "link3").symlink_to(external2_child)
        (self.scan_dir / "link4").symlink_to(external_dir2)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(
            result,
            {
                self.external_dir.resolve(),
                external_dir2.resolve(),
            },
        )

    def test_external_symlink_to_external_dir(self) -> None:
        """Test a symlink in an external dir points to another external dir."""
        external_dir2 = self.test_dir / "external2"
        external_dir2.mkdir()

        # Chain: scan/link1 -> external_dir
        (self.scan_dir / "link1").symlink_to(self.external_dir)
        # Chain: external_dir/link2 -> external_dir2
        (self.external_dir / "link2").symlink_to(external_dir2)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])

        self.assertEqual(
            result,
            {
                self.external_dir.resolve(),
                external_dir2.resolve(),
            },
        )

    def test_intermediate_external_symlink_chain(self) -> None:
        """Test a symlink chain that goes through an external symlink."""
        external_dir2 = self.test_dir / "external2"
        external_dir2.mkdir()

        intermediate_dir = self.test_dir / "intermediate"
        intermediate_dir.mkdir()

        # Chain: scan/link1 -> intermediate/link2 -> external2
        (intermediate_dir / "link2").symlink_to(external_dir2)
        (self.scan_dir / "link1").symlink_to(intermediate_dir / "link2")

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])

        self.assertEqual(
            result,
            {
                intermediate_dir.resolve() / "link2",
                external_dir2.resolve(),
            },
        )

    def test_bazel_handling_at_top_level(self) -> None:
        """Test bazel-* symlinks are ignored, but real dirs are not."""
        # This symlink to a directory should be ignored.
        bazel_dir_target = self.test_dir / "bazel-dir-target"
        bazel_dir_target.mkdir()
        (self.scan_dir / "bazel-dir").symlink_to(bazel_dir_target)

        # This symlink to a file should be ignored.
        bazel_file_target = self.test_dir / "bazel-file-target.txt"
        bazel_file_target.touch()
        (self.scan_dir / "bazel-file").symlink_to(bazel_file_target)

        # This REAL directory should NOT be ignored, and its contents scanned.
        bazel_real_dir = self.scan_dir / "bazel-real-dir"
        bazel_real_dir.mkdir()
        external_dir4 = self.test_dir / "external4"
        external_dir4.mkdir()
        (bazel_real_dir / "link_to_external4").symlink_to(external_dir4)

        # This symlink should be found.
        non_bazel_dir = self.scan_dir / "not-bazel"
        non_bazel_dir.mkdir()
        external_dir2 = self.test_dir / "external2"
        external_dir2.mkdir()
        (non_bazel_dir / "link_to_external2").symlink_to(external_dir2)

        # This symlink should also be found, as the exclusion is not recursive.
        sub_bazel_dir = non_bazel_dir / "bazel-sub"
        sub_bazel_dir.mkdir()
        external_dir3 = self.test_dir / "external3"
        external_dir3.mkdir()
        (sub_bazel_dir / "link_to_external3").symlink_to(external_dir3)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(
            result,
            {
                external_dir2.resolve(),
                external_dir3.resolve(),
                external_dir4.resolve(),
            },
        )

    def test_bazel_handling_recursively(self) -> None:
        """Test bazel-* symlinks are ignored recursively."""
        sub_dir = self.scan_dir / "sub"
        sub_dir.mkdir()

        # This symlink should be ignored.
        bazel_sub_dir_target = self.test_dir / "bazel-sub-dir-target"
        bazel_sub_dir_target.mkdir()
        (sub_dir / "bazel-dir").symlink_to(bazel_sub_dir_target)

        # This symlink should be found.
        non_bazel_dir = sub_dir / "not-bazel"
        non_bazel_dir.mkdir()
        external_dir = self.test_dir / "external_for_recursive"
        external_dir.mkdir()
        (non_bazel_dir / "link_to_external").symlink_to(external_dir)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(
            result,
            {
                external_dir.resolve(),
            },
        )

    def test_symlink_with_relative_path_to_external_dir(self) -> None:
        """Test symlink with a relative path to an external directory."""
        sub_dir = self.scan_dir / "sub"
        sub_dir.mkdir()
        link_path = sub_dir / "link_to_external"
        link_path.symlink_to("../../external")
        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])
        self.assertEqual(result, {self.external_dir.resolve()})

    def test_symlink_mount_preserves_both_paths(self) -> None:
        """Test that a symlink mount preserves both the original and resolved paths."""
        external_file = self.external_dir / "file.txt"
        external_file.touch()
        symlink_path = self.scan_dir / "symlink_to_file"
        symlink_path.symlink_to(external_file)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [symlink_path])
        self.assertIn(symlink_path, result)
        self.assertIn(external_file.resolve(), result)

    def test_venv_directory_is_ignored(self) -> None:
        """Test that .venv directories are not scanned."""
        venv_dir = self.scan_dir / ".venv"
        venv_dir.mkdir()

        (venv_dir / "link_to_external").symlink_to(self.external_dir)

        external_dir2 = self.test_dir / "external2"
        external_dir2.mkdir()
        (self.scan_dir / "link_to_external2").symlink_to(external_dir2)

        result = list_external_mounts.get_minimal_mounts(self.scan_dir, [])

        self.assertEqual(result, {external_dir2.resolve()})


class ListExternalMountsMainTest(unittest.TestCase):
    """
    Tests for the main function in list_external_mounts.
    """

    @patch("sys.stdout", new_callable=StringIO)
    @patch("pathlib.Path.cwd")
    @patch("scripts.list_external_mounts.get_minimal_mounts")
    def test_main_with_default_cwd(
        self,
        mock_get_minimal_mounts: MagicMock,
        mock_cwd: MagicMock,
        mock_stdout: MagicMock,
    ) -> None:
        """Test main uses current working directory by default."""
        mock_cwd.return_value = Path("/default/path")
        mock_get_minimal_mounts.return_value = {Path("/a/b"), Path("/c/d")}

        with patch("sys.argv", ["list_external_mounts.py"]):
            list_external_mounts.main()

        mock_get_minimal_mounts.assert_called_once_with(Path("/default/path"), [])
        self.assertEqual(sorted(mock_stdout.getvalue().splitlines()), ["/a/b", "/c/d"])

    @patch("sys.stdout", new_callable=StringIO)
    @patch("scripts.list_external_mounts.get_minimal_mounts")
    def test_main_with_custom_dir(
        self, mock_get_minimal_mounts: MagicMock, mock_stdout: MagicMock
    ) -> None:
        """Test main uses the directory provided in the command line."""
        mock_get_minimal_mounts.return_value = {Path("/e/f")}
        custom_dir = "/custom/dir"

        with patch("sys.argv", ["list_external_mounts.py", "--root-dir", custom_dir]):
            list_external_mounts.main()

        mock_get_minimal_mounts.assert_called_once_with(Path(custom_dir), [])
        self.assertEqual(sorted(mock_stdout.getvalue().splitlines()), ["/e/f"])

    @patch("sys.stdout", new_callable=StringIO)
    @patch("scripts.list_external_mounts.get_minimal_mounts")
    def test_main_with_mounts(
        self, mock_get_minimal_mounts: MagicMock, mock_stdout: MagicMock
    ) -> None:
        """Test main correctly handles additional mounts."""
        mock_get_minimal_mounts.return_value = {
            Path("/symlink/path"),
            Path("/mount/path1"),
            Path("/mount/path2"),
        }
        mount1 = "/mount/path1"
        mount2 = "/mount/path2"

        with patch(
            "sys.argv",
            ["list_external_mounts.py", "--mount", mount1, "--mount", mount2],
        ):
            list_external_mounts.main()

        self.assertEqual(
            sorted(mock_stdout.getvalue().splitlines()),
            ["/mount/path1", "/mount/path2", "/symlink/path"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
