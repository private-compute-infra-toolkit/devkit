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
This script finds project root.

It keeps moving up in the directory tree till it finds a /devkit directory.
If no /devkit directory provided, it return FileNotFoundError.
"""
import sys
import os
from pathlib import Path


def find_project_root() -> Path:
    """
    Finds the project root by searching for 'devkit'.
    It starts from the current directory and goes up until it finds a directory
    containing a 'devkit' file, directory, or symlink.
    """
    # Use PWD if available to preserve symlinks
    current_dir = Path(os.getenv("PWD", str(Path.cwd())))

    # Check current dir and all parents
    for path in [current_dir] + list(current_dir.parents):
        if (path / "devkit").exists():
            return path

    # Raise error if not found
    raise FileNotFoundError(
        "Could not find project root. Make sure you are in a devkit project."
    )


def main() -> None:
    try:
        root = find_project_root()
        print(root)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
