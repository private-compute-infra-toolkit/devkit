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
"""This file provides required logic to generate unit test coverage report"""

import argparse
import pathlib
import subprocess
import sys


class FileCoverage:
    """
    Holds and calculates coverage information for a single file.
    """

    def __init__(self, file_path: str):
        """
        Initializes the FileCoverage object.

        Args:
            file_path: The path to the source file.
        """
        self.file_path: str = file_path
        self.lines_found: int = 0
        self.lines_hit: int = 0
        self.branches_found: int = 0
        self.branches_hit: int = 0
        self.uncovered_lines: list[int] = []
        # Each tuple -> (line_number, block_id, branch_id)
        self.uncovered_branches: list[tuple[int, int, int]] = []

    def line_coverage_percent(self) -> float:
        """Calculates the line coverage percentage."""
        if self.lines_found == 0:
            return 1.0
        return self.lines_hit / self.lines_found

    def branch_coverage_percent(self) -> float:
        """Calculates the branch coverage percentage."""
        if self.branches_found == 0:
            return 1.0
        return self.branches_hit / self.branches_found

    def generate_summary_line(self) -> str:
        """Generates a formatted string for the main summary table."""
        return (
            f"{fit_to_column(self.file_path)} | "
            f"{self.line_coverage_percent():>7.2%} | "
            f"{self.branch_coverage_percent():>10.2%}"
        )

    def get_missing_branches_str(self) -> str:
        """Generates a report of uncovered branches,

        Each missing branch cover is in new row and is denoted as:
        Line <line_number>: (block: <block_id>, branch: <branch_id>)
        """
        if not self.uncovered_branches:
            return ""
        branch_report: list[str] = []
        for line, block, branch in self.uncovered_branches:
            branch_report.append(f"Line {line}: (block: {block}, branch: {branch})")

        return "\n".join(branch_report)

    def generate_missing_coverage_report(self) -> str:
        """
        Generates a detailed report of uncovered lines and branches for this file.

        Returns:
            An empty string if all lines/branches are covered, otherwise
            a report of uncovered lines/branches.
        """
        if not self.uncovered_lines and not self.uncovered_branches:
            return ""

        uncovered_lines_str = group_consecutive_numbers(self.uncovered_lines)
        uncovered_branches_str = self.get_missing_branches_str()
        report: list[str] = [f"\nFile: {self.file_path}\n"]
        if uncovered_lines_str:
            report.append(f"Lines to test: {uncovered_lines_str}\n")
        if uncovered_branches_str:
            report.append(f"Branches to test:\n{uncovered_branches_str}")

        return "".join(report)


def fit_to_column(filepath: str, max_width: int = 50) -> str:
    """Fits filepath to max column width.

    If length of filepath is below max_width, adds ' ' for string length
    to be exactly max_width.
    If length above max_width, adds '...' from left and part of a string
    exceeding max_width is cut from left (to see name of file).

    Args:
        filepath: Path to file which needs to be fit to column.
        max_width: Max string width.

    Returns:
        Fitted string with length equal to max_width.
    """
    filepath_length = len(filepath)
    if filepath_length > max_width:
        return "..." + filepath[-(max_width - 3) :]
    return filepath + " " * (max_width - filepath_length)


def print_and_validate_report(
    coverage_data: dict[str, FileCoverage],
    lines_threshold: float,
    branch_threshold: float,
) -> bool:
    """Prints a summary report and validates coverage against a threshold.

    Args:
        coverage_data: A dictionary of coverage data from the LCOV file.
        lines_threshold: Minimum line coverage threshold for a file.
        branch_threshold: Minimum branch coverage threshold for a file.

    Returns:
        True if all files meet the threshold, False otherwise.
    """
    is_coverage_valid = True
    overall_lines_coverage: float = 0.0
    overall_branch_coverage: float = 0.0
    n_files: int = len(coverage_data)

    print(f"{'file':<50} | {'Lines %':<.9} | Branches %")
    print("-" * 73)

    for file_coverage in coverage_data.values():
        print(file_coverage.generate_summary_line())
        lines_cov = file_coverage.line_coverage_percent()
        branch_cov = file_coverage.branch_coverage_percent()
        if lines_cov < lines_threshold or branch_cov < branch_threshold:
            is_coverage_valid = False

        overall_lines_coverage += lines_cov / n_files
        overall_branch_coverage += branch_cov / n_files

    # Print overall coverage
    print("-" * 73)
    print(
        f"{'Total':<50} | {overall_lines_coverage:>7.2%} | "
        f"{overall_branch_coverage:>10.2%}"
    )

    print("\n--- Missing Coverage ---")
    any_missing_coverage = False
    for file_coverage in coverage_data.values():
        report = file_coverage.generate_missing_coverage_report()
        if report:
            print(report)
            any_missing_coverage = True

    if not any_missing_coverage:
        print("All covered!")

    return is_coverage_valid


def group_consecutive_numbers(numbers: list[int]) -> str:
    """Groups lines numbers in a list.

    Example:
        [1, 2, 3, 6, 7, 10, 12, 13] -> (1-3, 6-7, 10, 12-13)

    Args:
        numbers: A list of lines number to group.

    Returns:
        String representation of grouped numbers.
    """
    if not numbers:
        return ""

    sorted_numbers = sorted(numbers)

    ranges: list[str] = []
    start_of_range = sorted_numbers[0]

    for i in range(1, len(sorted_numbers)):
        if sorted_numbers[i] != sorted_numbers[i - 1] + 1:
            end_of_range = sorted_numbers[i - 1]
            if start_of_range == end_of_range:
                ranges.append(str(start_of_range))
            else:
                ranges.append(f"{start_of_range}-{end_of_range}")
            start_of_range = sorted_numbers[i]

    end_of_range = sorted_numbers[-1]
    if start_of_range == end_of_range:
        ranges.append(str(start_of_range))
    else:
        ranges.append(f"{start_of_range}-{end_of_range}")

    return ", ".join(ranges)


def generate_lcov_report(
    file_path: pathlib.Path,
    lines_threshold: float,
    branch_threshold: float,
) -> bool:
    """
    Parses a bazel lcov file and prints a comprehensive coverage report.

    Args:
        file_path: Path to the bazel lcov file.
        lines_threshold: Minimum line coverage threshold for a file.
        branch_threshold: Minimum branch coverage threshold for a file.

    Returns:
        True if every file coverage is equal or above threshold, false otherwise.
    """
    # A dictionary to hold FileCoverage objects, keyed by file path.
    coverage_data: dict[str, FileCoverage] = {}
    current_file_path: str | None = None
    try:
        with file_path.open("r", encoding="utf-8") as lcov_file:
            # Read file line by line
            for line in lcov_file:
                line = line.strip()

                if line.startswith("SF:"):  # SF -> source file
                    # Start of a new file record
                    current_file_path = line.replace("SF:", "")
                    coverage_data[current_file_path] = FileCoverage(
                        file_path=current_file_path
                    )
                elif line == "end_of_record":
                    current_file_path = None
                elif current_file_path and current_file_path in coverage_data:
                    current_coverage = coverage_data[current_file_path]
                    parse_lcov_data_line(line, current_coverage)

            return print_and_validate_report(
                coverage_data, lines_threshold, branch_threshold
            )
    except FileNotFoundError:
        print(f"File not found: {file_path.as_posix()}")
        return False


def parse_lcov_data_line(line: str, current_coverage: FileCoverage) -> None:
    """Parses a single LCOV data line and updates the FileCoverage object.

    Args:
        line: Line from lcov file.
        current_coverage: Instance of FileCoverage for current file.

    Returns:
        None, it updates fields in current_coverage.
    """
    if line.startswith("LF:"):  # Lines found
        current_coverage.lines_found = int(line.replace("LF:", ""))
    elif line.startswith("LH:"):  # Lines hit
        current_coverage.lines_hit = int(line.replace("LH:", ""))
    elif line.startswith("BRF:"):  # Branches found
        current_coverage.branches_found = int(line.replace("BRF:", ""))
    elif line.startswith("BRH:"):  # Branches hit
        current_coverage.branches_hit = int(line.replace("BRH:", ""))
    elif line.startswith("DA:"):  # Line data
        parts = line.split(",")
        line_number = int(parts[0].replace("DA:", ""))
        hit_count = int(parts[1])
        if hit_count == 0:
            current_coverage.uncovered_lines.append(line_number)
    elif line.startswith("BRDA"):  # Branch data
        parts = line.split(",")
        line_number = int(parts[0].replace("BRDA:", ""))
        block_id = int(parts[1])
        branch_id = int(parts[2])
        # no hit is denoted as '-'
        hit_marker = parts[3]
        if hit_marker == "-":
            current_coverage.uncovered_branches.append(
                (line_number, block_id, branch_id)
            )


def run_bazel_coverage(target: str) -> pathlib.Path:
    """Runs `bazel coverage` for a specified target.

    Args:
        target: The Bazel test target to run coverage (e.g., '//...').

    Returns:
        The anticipated `pathlib.Path` to the generated coverage report file
        on successful execution.
    """
    command = ["bazel", "coverage", "--combined_report=lcov", target]
    try:
        subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=False,
            encoding="utf-8",
        )
        return pathlib.Path("bazel-out", "_coverage", "_coverage_report.dat")
    except subprocess.CalledProcessError as e:
        print(
            f"Error: Bazel coverage failed with exit code {e.returncode}.",
            file=sys.stderr,
        )
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"STDERR:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """
    Main function, parses arguments and run generate_lcov_report.
    """
    parser = argparse.ArgumentParser(
        prog="coverage",
        description="Generate unit test coverage report for Bazel workspace.",
        add_help=False,
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    parser.add_argument(
        "--target",
        type=str,
        help="Bazel test target.",
        default="//...",
    )
    parser.add_argument(
        "--lines",
        type=float,
        help=(
            "Threshold for the line coverage report to pass (in percentage). "
            "If any line coverage for a file is below threshold, script fails."
        ),
        default=100.0,
    )
    parser.add_argument(
        "--branch",
        type=float,
        help=(
            "Threshold for the branch coverage report to pass (in percentage). "
            "If any branch coverage for a file is below threshold, script fails."
        ),
        default=100.0,
    )

    args = parser.parse_args()

    for name, value in (("Branch", args.branch), ("Lines", args.lines)):
        if not 0.0 <= float(value) <= 100.0:
            print(f"Error: {name} threshold value must be in range [0.0, 100.0]")
            sys.exit(1)

    print("Running Bazel Coverage")
    report_path = run_bazel_coverage(args.target)

    print("Generating coverage report")
    coverage_passed = generate_lcov_report(
        report_path, float(args.lines) / 100, float(args.branch) / 100
    )

    if coverage_passed:
        print("Coverage check passed.")
    else:
        print("Coverage check failed.")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
