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
This script lists external mounts, including intermediate symlinks.
"""
import os
from pathlib import Path


def list_external_mounts(scan_dir: Path) -> set[Path]:
    """
    Scans a directory for symlinks and returns a minimal set of external paths
    they point to, including intermediate external symlinks.
    """
    scan_dir_abs = scan_dir.resolve()
    external_paths: set[Path] = set()

    worklist: list[Path] = [scan_dir_abs]
    scanned: set[Path] = set()

    while worklist:
        current_dir = worklist.pop(0)
        if current_dir in scanned:
            continue  # pragma: no cover
        scanned.add(current_dir)

        for root, dirs, files in os.walk(
            str(current_dir), topdown=True, followlinks=False
        ):
            root_path = Path(root)
            all_entries = dirs + files
            for name in all_entries:
                path = root_path / name
                if path.is_symlink():
                    if root_path == scan_dir_abs and name.startswith("bazel-"):
                        continue
                    _process_symlink(path, scan_dir_abs, external_paths, worklist)

    return _minimize_paths(external_paths)


def _process_symlink(
    path: Path, scan_dir_abs: Path, external_paths: set[Path], worklist: list[Path]
) -> None:
    """
    Resolves a symlink chain starting from `path`, adding any external paths
    to the `external_paths` set.
    """
    visited_in_chain: set[Path] = set()
    current_path = path

    while current_path.is_symlink():
        if current_path in visited_in_chain:
            # Cycle detected, stop processing this chain.
            return  # pragma: no cover
        visited_in_chain.add(current_path)

        try:
            target = current_path.readlink()
        except FileNotFoundError:  # pragma: no cover
            # The symlink was deleted between os.islink and os.readlink.
            return

        # Resolve the target path relative to the directory containing the symlink.
        abs_target = current_path.parent / target

        if not abs_target.exists():
            # Broken symlink, stop processing this chain.
            return

        # Check if the target is outside the scan directory.
        common = os.path.commonpath([str(scan_dir_abs), str(abs_target)])
        if os.path.normpath(common) != str(scan_dir_abs):
            norm_target = Path(os.path.normpath(str(abs_target)))
            if norm_target not in external_paths:
                external_paths.add(norm_target)
                if norm_target.is_dir():
                    worklist.append(norm_target)

        current_path = abs_target


def _minimize_paths(paths: set[Path]) -> set[Path]:
    """
    Given a set of paths, returns a new set containing only the minimal parent paths.
    For example: {'/a/b', '/a/b/c', '/d'} -> {'/a/b', '/d'}
    """
    # Sort paths to ensure that when comparing, we are consistent.
    sorted_paths = sorted(list(paths))
    minimal_paths: set[Path] = set()

    for path in sorted_paths:
        # If path is a subpath of a path already in minimal_paths, skip it.
        if any(path.is_relative_to(p) for p in minimal_paths):
            continue

        # Remove any paths from minimal_paths that are subpaths of the current path.
        minimal_paths.difference_update(
            {p for p in minimal_paths if p.is_relative_to(path)}
        )

        minimal_paths.add(path)

    return minimal_paths


if __name__ == "__main__":  # pragma: no cover
    for p in list_external_mounts(Path.cwd()):
        print(p)
