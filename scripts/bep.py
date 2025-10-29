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

"""
This file provides necessary logic to generate BEP.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd_args: list[str], capture_output: bool = False) -> str:
    """Run commands and handles exceptions.

    Args:
        cmd_args: list of arguments to run
        capture_output: True if process output should be returned, false otherwise

    Returns:
        process output if if `capture_output` is True, empty string otherwise
    """
    print(f"Executing: {' '.join(cmd_args)}")
    try:

        result = subprocess.run(
            cmd_args,
            check=True,
            text=True,
            capture_output=capture_output,
            encoding="utf-8",
        )
        if capture_output:
            return result.stdout.strip()
        return ""
    except subprocess.CalledProcessError as e:
        print(
            f"Error: Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}.",
            file=sys.stderr,
        )
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"STDERR:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd_args[0]}", file=sys.stderr)
        sys.exit(1)


def generate_build_event_json(
    bazel_target: str, output_path: Path, bazel_command: str
) -> None:
    """Generates BEP for bazel_target.

    Args:
        bazel_target: bazel target to generate BEP
        output_path: path to output file with BEP in json
        bazel_command: bazel command used to get BEP ('build' or 'fetch')

    Returns:
        None, it saves BEP to `output_path` file
    """
    with (
        tempfile.TemporaryDirectory() as bazel_cache_dir,
        tempfile.TemporaryDirectory() as bazel_registry_cache_dir,
    ):
        bash_command = [
            "bazel",
            f"--output_base={bazel_cache_dir}",
            bazel_command,
            f"--build_event_json_file={output_path}",
            f"--repository_cache={bazel_registry_cache_dir}",
            bazel_target,
        ]
        # ignore remote cache with `bazel build`
        if bazel_command == "build":
            bash_command.append("--noremote_accept_cached")
        run_command(bash_command)


def _process_target_and_save(
    bazel_target: str, output_file: Path, command: str
) -> None:
    """Helper to process a single Bazel target and save its BEP.

    Args:
        bazel_target: bazel target to generate BEP
        output_file: path to output file with BEP in json
        command: bazel command used to get BEP ('build' or 'fetch')
    """
    print(f"\n--- Processing: {bazel_target} ---")
    generate_build_event_json(bazel_target, output_file, command)
    print(f"--- Finished processing {bazel_target} ---")


def generate_bazel_events_folder(
    targets: list[str],
    command: str,
    output_dir: Path,
) -> None:
    """Calls `generate_build_event_json` for every bazel target in a list.

    If the targets list is empty, it generates a single 'bep.json'.
    Otherwise, it generates '<target_name>/bep.json' for each specified target.

    Args:
        targets: list of bazel targets to generate BEP
        command: bazel command used to get BEP ('build' or 'fetch')
        output_dir: path to directory in which BEP files will be stored

    Returns:
        None, it generated BEP file for every target
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(targets) == 0:
        _process_target_and_save("//...", output_dir / "bep.json", command)
    else:
        for bazel_target in targets:
            # Replacing ':' with '_' to avoid problems with file naming
            sanitized_target_name = bazel_target.replace(":", "_").split("/")[-1]
            output_file = output_dir / sanitized_target_name / "bep.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            _process_target_and_save(bazel_target, output_file, command)


def main() -> None:
    """
    Main function, parses arguments and run generate_bazel_events_folder.

    Without any arguments BEP will be created with 'fetch' command for all targets
    and stored in a directory named 'bazel-bep'.
    """
    parser = argparse.ArgumentParser(
        prog="bep",
        description=(
            "Generates Bazel Build Event Protocol (BEP) JSON files "
            "for a list of targets."
        ),
        add_help=False,
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    # If target is not provided BEP will be generated for all targets (bazel fetch //...)
    parser.add_argument(
        "--targets",
        nargs="+",  # One or more arguments
        help="A list of Bazel targets to process.",
        default=[],
    )
    parser.add_argument(
        "--command",
        choices=["fetch", "build"],
        help="The Bazel command to run ('fetch' or 'build').",
        type=str,
        default="fetch",
    )
    parser.add_argument(
        "--output_dir",
        help="Output directory for BEP logs.",
        type=Path,
        default=Path("bazel-bep"),
    )

    args = parser.parse_args()

    generate_bazel_events_folder(args.targets, args.command, args.output_dir)
    print("All targets processed successfully.")


if __name__ == "__main__":  # pragma: no cover
    main()
