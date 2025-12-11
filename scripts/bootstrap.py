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
This script instantiates project templates.
"""

import argparse
from collections.abc import Mapping
import os
from pathlib import Path
import shutil
import sys
import jinja2


def copy_and_template(
    src_dir: Path, dest_dir: Path, context: Mapping[str, str]
) -> bool:
    """
    Recursively copies a directory and applies Jinja2 templating to each file.

    Args:
        src_dir (Path): The source directory.
        dest_dir (Path): The destination directory.
        context (Mapping): The context to use for templating.
    Returns:
        bool: True if any error occurred, False otherwise.
    """
    error_occurred = False
    for src_path, _, src_files in src_dir.walk(follow_symlinks=True):
        for src_file in src_files:
            if src_file.endswith(".include"):
                continue
            src_file_path = src_path / src_file
            relative_path = src_file_path.relative_to(src_dir)
            dest_file_path = dest_dir / relative_path
            dest_file_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with src_file_path.open("r", encoding="utf-8") as f:
                    content = f.read()
                    env = jinja2.Environment(
                        loader=jinja2.FileSystemLoader(src_dir),
                        undefined=jinja2.StrictUndefined,
                    )
                    template = env.from_string(content)
                with dest_file_path.open("w", encoding="utf-8") as f:
                    f.write(template.render(context))
                    f.write("\n")
                shutil.copymode(src_file_path, dest_file_path)
            except jinja2.exceptions.TemplateSyntaxError as e:
                error_occurred = True
                print(f"Error in template: {src_file_path}", file=sys.stderr)
                print(f"  Line {e.lineno}: {e.message}", file=sys.stderr)
                lines = content.splitlines()
                for i in range(max(0, e.lineno - 4), min(len(lines), e.lineno + 3)):
                    print(
                        f"    {i + 1:4d}{' >' if i + 1 == e.lineno else '  '} {lines[i]}",
                        file=sys.stderr,
                    )
            except jinja2.exceptions.UndefinedError as e:
                error_occurred = True
                print(f"Error in template: {src_file_path}", file=sys.stderr)
                print(f"  {e.message}", file=sys.stderr)
    return error_occurred


def main() -> None:
    """The main function of the bootstrap script."""
    parser = argparse.ArgumentParser(
        prog="bootstrap",
        description="Bootstraps a new project from a template.",
        formatter_class=argparse.RawTextHelpFormatter,
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
        "--template",
        required=True,
        help="The name of the template to use.",
    )
    parser.add_argument(
        "--templates-root", help="The root directory for templates lookup.", type=Path
    )
    parser.add_argument(
        "--output-dir",
        help="The directory where the project will be bootstrapped. "
        "Defaults to current directory.",
        type=Path,
        default=Path(os.getcwd()),
    )
    parser.add_argument(
        "--args",
        nargs="*",
        help="A list of key=value pairs for templating.",
        default=[],
    )
    args = parser.parse_args()

    template = args.template
    context = {}
    for arg in args.args:
        if "=" not in arg:
            print(f"Invalid argument: {arg}. Expected key=value.", file=sys.stderr)
            sys.exit(1)
        key, value = arg.split("=", 1)
        context[key] = value

    dest_dir = args.output_dir
    if args.templates_root:
        templates_root_dir = args.templates_root
    else:
        script_dir = Path(__file__).parent
        templates_root_dir = script_dir.parent / "templates"
    template_dir = (templates_root_dir / template).resolve()

    try:
        template_dir = template_dir.resolve(strict=True)
    except FileNotFoundError:
        print(f"Template '{template}' not found at '{template_dir}'", file=sys.stderr)
        sys.exit(1)

    try:
        if copy_and_template(template_dir, dest_dir, context):
            print("Errors occurred during templating.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Project bootstrapped with '{template}' template.")


if __name__ == "__main__":  # pragma: no cover
    main()
