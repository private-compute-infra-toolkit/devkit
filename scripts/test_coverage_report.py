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

"""Unit Tests for generating coverage report"""

import io
import subprocess
import sys
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.resolve(strict=True)))
from coverage_report import (
    FileCoverage,
    fit_to_column,
    group_consecutive_numbers,
    parse_lcov_data_line,
    generate_lcov_report,
    print_and_validate_report,
    run_bazel_coverage,
    main,
)


class TestFileCoverage(unittest.TestCase):
    """Tests for the FileCoverage class."""

    def setUp(self) -> None:
        """Set up a common FileCoverage instance for tests."""
        self.coverage = FileCoverage("path/to/file.py")

    def test_line_coverage_percent(self) -> None:
        self.coverage.lines_found = 10
        self.coverage.lines_hit = 8
        self.assertAlmostEqual(0.8, self.coverage.line_coverage_percent())

    def test_line_coverage_no_lines_found(self) -> None:
        self.coverage.lines_found = 0
        self.assertEqual(1.0, self.coverage.line_coverage_percent())

    def test_branch_coverage_percent(self) -> None:
        self.coverage.branches_found = 4
        self.coverage.branches_hit = 1
        self.assertAlmostEqual(0.25, self.coverage.branch_coverage_percent())

    def test_branch_coverage_no_branches_found(self) -> None:
        self.coverage.branches_found = 0
        self.assertEqual(1.0, self.coverage.branch_coverage_percent())

    def test_generate_missing_line_coverage_report(self) -> None:
        self.coverage.uncovered_lines = [5, 6, 8, 10, 11]
        expected = "\nFile: path/to/file.py\nLines to test: 5-6, 8, 10-11\n"
        self.assertEqual(expected, self.coverage.generate_missing_coverage_report())

    def test_generate_missing_coverage_report_when_all_covered(self) -> None:
        self.coverage.uncovered_lines = []
        self.assertEqual("", self.coverage.generate_missing_coverage_report())

    def test_generate_missing_line_branches_coverage_report(self) -> None:
        """Tests generating missing coverage report with lines and branches"""
        self.coverage.uncovered_lines = [5, 6, 8, 10, 11]
        self.coverage.uncovered_branches = [(1, 1, 1), (1, 2, 3)]
        expected = """
File: path/to/file.py
Lines to test: 5-6, 8, 10-11
Branches to test:
Line 1: (block: 1, branch: 1)
Line 1: (block: 2, branch: 3)"""
        self.assertEqual(expected, self.coverage.generate_missing_coverage_report())

    def test_generate_missing_coverage_report_with_branches_only(self) -> None:
        """Tests generating missing coverage report with only branches missing"""
        self.coverage.uncovered_branches = [(2, 1, 1), (1, 2, 3)]
        expected = "Line 2: (block: 1, branch: 1)\nLine 1: (block: 2, branch: 3)"
        self.assertEqual(expected, self.coverage.get_missing_branches_str())


class TestHelperFunctions(unittest.TestCase):
    """Tests for standalone helper functions."""

    def test_fit_to_column_pads_short_string(self) -> None:
        self.assertEqual("test      ", fit_to_column("test", 10))
        self.assertEqual(10, len(fit_to_column("test", 10)))

    def test_fit_to_column_truncates_long_string(self) -> None:
        path = "source/project/module/very_long_file_name.py"
        expected = "...dule/very_long_file_name.py"
        self.assertEqual(expected, fit_to_column(path, 30))
        self.assertEqual(30, len(fit_to_column(path, 30)))

    def test_group_consecutive_numbers_sorted(self) -> None:
        numbers = [1, 2, 3, 6, 7, 10, 12, 13]
        self.assertEqual("1-3, 6-7, 10, 12-13", group_consecutive_numbers(numbers))

    def test_group_consecutive_numbers_random_order(self) -> None:
        numbers = [13, 1, 12, 3, 6, 10, 2, 7]
        self.assertEqual("1-3, 6-7, 10, 12-13", group_consecutive_numbers(numbers))

    def test_group_consecutive_numbers_empty_list(self) -> None:
        self.assertEqual("", group_consecutive_numbers([]))


class TestLcovParsingAndReporting(unittest.TestCase):
    """Tests for LCOV file parsing and report generation logic."""

    def test_parse_lcov_data_line(self) -> None:
        """Test parsing of different line types"""
        cov = FileCoverage("a.py")
        parse_lcov_data_line("LF:10", cov)
        self.assertEqual(10, cov.lines_found)
        parse_lcov_data_line("LH:5", cov)
        self.assertEqual(5, cov.lines_hit)
        parse_lcov_data_line("BRF:4", cov)
        self.assertEqual(4, cov.branches_found)
        parse_lcov_data_line("BRH:2", cov)
        self.assertEqual(2, cov.branches_hit)
        parse_lcov_data_line("DA:1,0", cov)
        self.assertEqual([1], cov.uncovered_lines)
        parse_lcov_data_line("DA:2,1", cov)  # Should not be added
        self.assertEqual([1], cov.uncovered_lines)

    def test_parse_lcov_data_branches(self) -> None:
        """Tests parsing lcov line with branch data"""
        cov = FileCoverage("a.py")
        parse_lcov_data_line("BRDA:53,0,1,1", cov)
        parse_lcov_data_line("BRDA:53,0,0,-", cov)
        self.assertNotIn((53, 0, 1), cov.uncovered_branches)
        self.assertIn((53, 0, 0), cov.uncovered_branches)

    @patch("coverage_report.print_and_validate_report")
    def test_generate_lcov_report_success(self, mock_print_validate: MagicMock) -> None:
        """Test final report output after successful parsing."""
        lcov_content = """
SF:source/main.py
LF:10
LH:8
BRF:2
BRH:1
DA:3,0
DA:5,0
end_of_record
"""
        mock_file = mock_open(read_data=lcov_content)
        with patch("pathlib.Path.open", mock_file):
            generate_lcov_report(Path("fake.dat"), 80, 80)

        # Check that the parsing was correct before calling the print function
        self.assertTrue(mock_print_validate.called)
        call_args, _ = mock_print_validate.call_args
        coverage_data = call_args[0]
        self.assertIn("source/main.py", coverage_data)
        self.assertEqual(10, coverage_data["source/main.py"].lines_found)
        self.assertEqual(8, coverage_data["source/main.py"].lines_hit)
        self.assertEqual([3, 5], coverage_data["source/main.py"].uncovered_lines)

    def test_generate_lcov_report_file_not_found(self) -> None:
        result = generate_lcov_report(Path("nonexistent.dat"), 100, 100)
        self.assertFalse(result)

    def test_print_and_validate_report_returns_true_on_success(self) -> None:
        """
        Tests that the function returns True when all files meet the coverage threshold.
        """
        # All files have coverage >= 90%
        cov_success1 = FileCoverage("a.py")
        cov_success1.lines_found = 10
        cov_success1.lines_hit = 10  # 100%

        cov_success2 = FileCoverage("b.py")
        cov_success2.lines_found = 10
        cov_success2.lines_hit = 9  # 90%

        coverage_data = {"a.py": cov_success1, "b.py": cov_success2}

        string_io = io.StringIO()
        with redirect_stdout(string_io):
            is_valid = print_and_validate_report(coverage_data, 0.9, 0.9)

        output = string_io.getvalue()
        self.assertIn("a.py", output)
        self.assertIn("100.00%", output)
        self.assertIn("b.py", output)
        self.assertIn("90.00%", output)
        self.assertTrue(is_valid)

    def test_print_and_validate_report_returns_false_on_lines_cov_failure(self) -> None:
        """
        Tests that the function returns False when at least one file is
        below the coverage threshold.
        """
        # One file has line coverage < 90%
        cov_success = FileCoverage("a.py")
        cov_success.lines_found = 10
        cov_success.lines_hit = 10  # 100%

        cov_fail = FileCoverage("b.py")
        cov_fail.lines_found = 10
        cov_fail.lines_hit = 5  # 50% (below threshold)

        coverage_data = {"a.py": cov_success, "b.py": cov_fail}

        string_io = io.StringIO()
        with redirect_stdout(string_io):
            is_valid = print_and_validate_report(coverage_data, 90, 90)

        output = string_io.getvalue()
        self.assertIn("a.py", output)
        self.assertIn("b.py", output)
        self.assertIn("50.00%", output)  # Check for the failing percentage
        self.assertFalse(is_valid)

    def test_print_and_validate_report_returns_false_on_branch_cov_failure(
        self,
    ) -> None:
        """
        Tests that the function returns False when at least one file is
        below the coverage threshold.
        """
        # One file has line coverage < 90%
        cov_success = FileCoverage("a.py")
        cov_success.branches_found = 10
        cov_success.branches_hit = 10  # 100%

        cov_fail = FileCoverage("b.py")
        cov_fail.branches_found = 10
        cov_fail.branches_hit = 5  # 50% (below threshold)

        coverage_data = {"a.py": cov_success, "b.py": cov_fail}

        string_io = io.StringIO()
        with redirect_stdout(string_io):
            is_valid = print_and_validate_report(coverage_data, 90, 90)

        output = string_io.getvalue()
        self.assertIn("a.py", output)
        self.assertIn("b.py", output)
        self.assertIn("50.00%", output)  # Check for the failing percentage
        self.assertFalse(is_valid)

    def test_report_prints_details_when_coverage_is_missing(self) -> None:
        """
        Tests that if a missing coverage report is generated, it is printed
        and the final 'All covered!' message is suppressed.
        """
        cov_fail = FileCoverage("imperfect.py")
        cov_fail.uncovered_lines = [15]

        cov_ok = FileCoverage("perfect.py")

        coverage_data = {"imperfect.py": cov_fail, "perfect.py": cov_ok}

        string_io = io.StringIO()
        with redirect_stdout(string_io):
            print_and_validate_report(coverage_data, 100, 100)

        output = string_io.getvalue()

        self.assertIn("File: imperfect.py", output)
        self.assertIn("Lines to test: 15", output)

        self.assertNotIn("All covered!", output)


class TestMainExecution(unittest.TestCase):
    """Tests for functions with side effects like subprocess and sys.exit."""

    @patch("subprocess.run")
    def test_run_bazel_coverage_success(self, mock_subprocess_run: MagicMock) -> None:
        """Tests if run_bazel_coverage returns correct path after successful run."""
        result = run_bazel_coverage("//...")
        mock_subprocess_run.assert_called_once_with(
            ["bazel", "coverage", "--combined_report=lcov", "//..."],
            check=True,
            text=True,
            capture_output=False,
            encoding="utf-8",
        )
        self.assertEqual(Path("bazel-out", "_coverage", "_coverage_report.dat"), result)

    @patch("sys.exit")
    @patch("subprocess.run")
    def test_run_bazel_coverage_failure(
        self, mock_subprocess_run: MagicMock, mock_sys_exit: MagicMock
    ) -> None:
        # Configure the mock to raise CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        run_bazel_coverage("//...")
        mock_sys_exit.assert_called_once_with(1)

    @patch("sys.argv", ["coverage_report.py", "--target", "//..."])
    @patch("sys.exit")
    @patch("coverage_report.generate_lcov_report")
    @patch("coverage_report.run_bazel_coverage")
    def test_main_logic(
        self,
        mock_run_bazel: MagicMock,
        mock_generate_report: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """
        Tests if main works properly according to the return value
        from generate report.
        """

        # Main should not fail in this case
        mock_generate_report.return_value = True
        main()
        mock_run_bazel.assert_called_once_with("//...")
        mock_sys_exit.assert_not_called()

        mock_run_bazel.reset_mock()
        mock_generate_report.reset_mock()
        mock_sys_exit.reset_mock()

        # Main should fail
        mock_generate_report.return_value = False
        main()
        mock_run_bazel.assert_called_once_with("//...")
        mock_sys_exit.assert_called_once_with(1)

    @patch("sys.argv", ["coverage_report.py", "--lines", "105"])
    @patch("coverage_report.generate_lcov_report")
    @patch("coverage_report.run_bazel_coverage")
    @patch("sys.exit")
    def test_main_exits_if_lines_threshold_is_too_high(
        self,
        mock_sys_exit: MagicMock,
        mock_run_bazel: MagicMock,
        mock_generate_report: MagicMock,
    ) -> None:
        """Tests that main exits if lines coverage threshold > 100."""
        mock_sys_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

        mock_run_bazel.assert_not_called()
        mock_generate_report.assert_not_called()

    @patch("sys.argv", ["coverage_report.py", "--branch", "105"])
    @patch("coverage_report.generate_lcov_report")
    @patch("coverage_report.run_bazel_coverage")
    @patch("sys.exit")
    def test_main_exits_if_branch_threshold_is_too_high(
        self,
        mock_sys_exit: MagicMock,
        mock_run_bazel: MagicMock,
        mock_generate_report: MagicMock,
    ) -> None:
        """Tests that main exits if branch coverage report > 100."""
        mock_sys_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

        mock_run_bazel.assert_not_called()
        mock_generate_report.assert_not_called()

    @patch("sys.argv", ["coverage_report.py", "--lines", "-12.25"])
    @patch("coverage_report.generate_lcov_report")
    @patch("coverage_report.run_bazel_coverage")
    @patch("sys.exit")
    def test_main_exits_if_lines_threshold_is_too_low(
        self,
        mock_sys_exit: MagicMock,
        mock_run_bazel: MagicMock,
        mock_generate_report: MagicMock,
    ) -> None:
        """Tests that main exits if lines coverage threshold < 0.0."""
        mock_sys_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

        mock_run_bazel.assert_not_called()
        mock_generate_report.assert_not_called()

    @patch("sys.argv", ["coverage_report.py", "--branch", "-12.25"])
    @patch("coverage_report.generate_lcov_report")
    @patch("coverage_report.run_bazel_coverage")
    @patch("sys.exit")
    def test_main_exits_if_branch_threshold_is_too_low(
        self,
        mock_sys_exit: MagicMock,
        mock_run_bazel: MagicMock,
        mock_generate_report: MagicMock,
    ) -> None:
        """Tests that main exits if branch coverage threshold < 0.0."""
        mock_sys_exit.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

        mock_run_bazel.assert_not_called()
        mock_generate_report.assert_not_called()

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("coverage_report.subprocess.run")
    def test_run_bazel_coverage_prints_error_on_failure(
        self, mock_subprocess_run: MagicMock, mock_stderr: io.StringIO
    ) -> None:
        """
        Tests that run_bazel_coverage prints details to stderr
        when a CalledProcessError is raised.
        """
        cmd = ["bazel", "coverage", "//fail"]
        stdout_output = "Some build output log."
        stderr_output = "FATAL: Build failed spectacularly."
        error = subprocess.CalledProcessError(
            returncode=1, cmd=cmd, output=stdout_output, stderr=stderr_output
        )
        mock_subprocess_run.side_effect = error

        with self.assertRaises(SystemExit) as cm:
            run_bazel_coverage("//fail")

        self.assertEqual(cm.exception.code, 1)

        output = mock_stderr.getvalue()

        self.assertIn("Error: Bazel coverage failed with exit code 1.", output)
        self.assertIn(f"STDOUT:\n{stdout_output}", output)
        self.assertIn(f"STDERR:\n{stderr_output}", output)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
