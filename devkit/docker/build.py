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
This script manages the building of Docker images with content-addressable tagging.
"""

import argparse
import hashlib
import os
import subprocess
import sys
from typing import List, Dict, Optional, TypedDict
import json
import graphlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = ""
ARCH = "amd64"


def load_config(config_path: str) -> None:
    """Loads the devkit.json config file."""
    global REPO
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
                if "docker" in config and "registry" in config["docker"]:
                    REPO = config["docker"]["registry"]
            except json.JSONDecodeError as e:
                print(f"Error: Could not decode {config_path}: {e}")
                sys.exit(1)


class ImageConfig(TypedDict):
    deps: Dict[str, str]


ImageConfigsMap = Dict[str, ImageConfig]


def load_image_configs(search_paths: List[str]) -> ImageConfigsMap:
    """Loads all deps.json files from the search paths."""
    all_configs: ImageConfigsMap = {}
    for path in search_paths:
        deps_file = os.path.join(path, "deps.json")
        if os.path.exists(deps_file):
            print(f"Loading image configs from {deps_file}")
            with open(deps_file, "r", encoding="utf-8") as f:
                try:
                    configs = json.load(f)
                    if isinstance(configs, dict):
                        all_configs.update(configs)
                    else:
                        print(
                            f"Warning: {deps_file} does not contain a dict of configs."
                        )
                except json.JSONDecodeError as e:
                    print(f"Error: Could not decode {deps_file}: {e}")
                    sys.exit(1)
    return all_configs


def calculate_sha256(dockerfile_path: str, sorted_build_args: List[str]) -> str:
    """
    Calculates SHA256 hash based on Dockerfile content and sorted build arguments.
    """
    hasher = hashlib.sha256()

    with open(dockerfile_path, "rb") as f:
        hasher.update(f.read())

    for arg_val_pair in sorted_build_args:
        hasher.update(arg_val_pair.encode("utf-8"))

    return hasher.hexdigest()


def get_image_tag(image_name: str, sha: str) -> str:
    """Constructs the full image tag."""
    image_path = f"devkit/{image_name}"
    tag_suffix = f"{ARCH}-{sha}"
    if REPO:
        return f"{REPO}/{image_path}:{tag_suffix}"
    return f"{image_path}:{tag_suffix}"


def manage_docker_image(
    tag: str,
    dockerfile_path: str,
    build_args_list: List[str],
    context_path: str,
) -> None:
    """
    Checks if a Docker image exists, pulls it if available in registry,
    or builds and pushes it otherwise.
    Args:
        tag: The full tag of the image.
        dockerfile_path: Absolute path to the Dockerfile.
        build_args_list: A list of build arguments,
          e.g., ["ARG_NAME1", "VALUE1", "ARG_NAME2", "VALUE2"].
        context_path: The Docker build context path.
    """
    try:
        # 1. Check if image exists locally
        print(f"Checking for local image: {tag}")
        inspect_cmd = ["docker", "image", "inspect", tag]
        inspect_result = subprocess.run(
            inspect_cmd, capture_output=True, text=True, check=False
        )

        if inspect_result.returncode == 0:
            print(f"Image {tag} already exists locally. Skipping build/pull.")
            return

        # 2. If not local, check manifest remotely
        print(f"Checking for remote image manifest: {tag}")
        manifest_inspect_cmd = ["docker", "manifest", "inspect", tag]
        manifest_result = subprocess.run(
            manifest_inspect_cmd, capture_output=True, text=True, check=False
        )

        if manifest_result.returncode == 0:
            print(f"Image {tag} found in remote registry. Pulling...")
            pull_cmd = ["docker", "pull", tag]
            process = subprocess.run(
                pull_cmd, check=True, text=True, capture_output=True
            )
            if process.stdout:
                print(process.stdout.strip())
            if process.stderr:
                print(process.stderr.strip())
            print(f"Image {tag} pulled successfully.")
            return

        # 4. If manifest does not exist, build and push
        print(f"Image {tag} not found locally or in remote registry. Building...")

        docker_build_cmd = [
            "docker",
            "buildx",
            "build",
            "--tag",
            tag,
            "--file",
            dockerfile_path,
        ]

        idx = 0
        while idx < len(build_args_list):
            arg_name = build_args_list[idx]
            arg_value = build_args_list[idx + 1]
            docker_build_cmd.append("--build-arg")
            docker_build_cmd.append(f"{arg_name}={arg_value}")
            idx += 2

        docker_build_cmd.append(context_path)  # Docker build context

        print(f"Executing build: {' '.join(docker_build_cmd)}")
        process = subprocess.run(
            docker_build_cmd, check=True, text=True, capture_output=True
        )
        if process.stdout:
            print(process.stdout.strip())
        if process.stderr:
            print(process.stderr.strip())
        print(f"Image {tag} built successfully.")

        print(f"Pushing image {tag}...")
        push_cmd = ["docker", "push", tag]
        push_result = subprocess.run(
            push_cmd, check=False, text=True, capture_output=True
        )
        if push_result.returncode == 0:
            if push_result.stdout:
                print(push_result.stdout.strip())
            if push_result.stderr:
                print(push_result.stderr.strip())
            print(f"Image {tag} pushed successfully.")
        else:
            print(
                f"Warning: Failed to push image {tag}. " "Continuing with local image."
            )
            if push_result.stderr:
                print(f"Details: {push_result.stderr.strip()}")

    except subprocess.CalledProcessError as e:
        print(f"Error during Docker operation for {tag}:")
        print(f"Command: {' '.join(e.cmd)}")
        if e.stdout:
            print(f"Stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"Stderr: {e.stderr.strip()}")
        sys.exit(e.returncode if e.returncode != 0 else 1)
    except FileNotFoundError:
        print(
            "Error: Docker command not found. "
            "Please ensure Docker is installed and in PATH.",
        )
        sys.exit(1)


def process_image(
    image_name: str,
    dependencies: Dict[str, str],
    generated_tags: Dict[str, str],
    print_tag_mode: bool,
    target_image_for_tag_print: Optional[str],
    search_paths: List[str],
) -> Optional[str]:
    """
    Processes a single image: calculates its tag, builds/pulls/pushes it,
    and optionally prints the tag.
    """
    print(f"\n=== Processing: {image_name} ===")
    dockerfile_name = f"{image_name}.Dockerfile"
    dockerfile_path = None

    for path in search_paths:
        potential_path = os.path.join(path, dockerfile_name)
        if os.path.exists(potential_path):
            dockerfile_path = potential_path
            break

    if not dockerfile_path:
        print(
            f"Error: Dockerfile {dockerfile_name} not found for image "
            f"'{image_name}' in any of the search paths: {search_paths}."
        )
        sys.exit(1)

    dockerfile_path = os.path.realpath(dockerfile_path)

    build_args_for_manage = []  # For calling manage_image: [ARG_NAME, ARG_VALUE, ...]
    build_args_for_sha_calc = []  # For SHA calculation: ["ARG_NAME=VALUE", ...]

    for arg_name, dep_image_name in dependencies.items():
        if dep_image_name not in generated_tags:
            print(
                f"Error: Dependency tag for '{dep_image_name}' (needed by "
                f"'{image_name}' as build arg '{arg_name}') not found."
            )
            print(
                "Ensure images are in the correct build order and all "
                "dependencies are defined correctly."
            )
            sys.exit(1)

        dep_tag = generated_tags[dep_image_name]
        build_args_for_manage.extend([arg_name, dep_tag])
        build_args_for_sha_calc.append(f"{arg_name}={dep_tag}")
        print(
            f"Build arg for {image_name}: {arg_name}={dep_image_name} "
            f"(Tag: {dep_tag})"
        )

    build_args_for_sha_calc.sort()

    try:
        current_sha = calculate_sha256(dockerfile_path, build_args_for_sha_calc)
    except FileNotFoundError:  # Should be caught by os.path.exists, but defensive.
        print(
            f"Error: Dockerfile {dockerfile_path} disappeared before SHA "
            f"calculation for image {image_name}."
        )
        sys.exit(1)

    sha_info_str = (
        f"SHA for {dockerfile_path} (Content + Sorted Build Args "
        f"[{', '.join(build_args_for_sha_calc)}]): {current_sha}"
    )
    print(sha_info_str)

    current_tag = get_image_tag(image_name, current_sha)
    print(f"Tag for {image_name}: {current_tag}")
    generated_tags[image_name] = current_tag

    context_path = os.path.dirname(dockerfile_path)
    manage_docker_image(
        current_tag, dockerfile_path, build_args_for_manage, context_path
    )

    if print_tag_mode:
        if image_name == target_image_for_tag_print:
            print(current_tag)
            sys.exit(0)
    else:
        # manage_docker_image handles its own print and sys.exit calls on error.
        # If it returns, it was successful.
        print(
            f"=== Finished processing: {image_name} ===",
        )

    return current_tag


def get_dependency_subgraph(
    target_image_name: str,
    image_configs_map: Dict[str, ImageConfig],
) -> List[str]:
    """
    Performs a DFS traversal to find all dependencies for a target image,
    then returns a topologically sorted list of these dependencies.
    """
    if target_image_name not in image_configs_map:
        return []

    # Build the full dependency graph for graphlib
    full_graph = {
        name: set(conf["deps"].values()) for name, conf in image_configs_map.items()
    }

    # Find all nodes reachable from the target_image_name (i.e., its dependencies)
    nodes_to_visit = {target_image_name}
    visited_nodes = set()
    while nodes_to_visit:
        current_node = nodes_to_visit.pop()
        if current_node not in visited_nodes:
            visited_nodes.add(current_node)
            # Add dependencies of the current node to the visit list
            # This assumes deps are keys in the full_graph
            if current_node in full_graph:
                nodes_to_visit.update(full_graph[current_node])

    # Create a subgraph containing only the target and its dependencies
    subgraph = {node: full_graph[node] for node in visited_nodes if node in full_graph}

    # Topologically sort the subgraph to get the correct build order
    try:
        ts = graphlib.TopologicalSorter(subgraph)
        return list(ts.static_order())
    except graphlib.CycleError as e:
        # This should ideally not happen if the full graph is acyclic,
        # but it's good practice to handle it.
        print(f"Error: Cycle detected in dependencies for {target_image_name}: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Docker images with content-addressable tagging.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "target_image",
        nargs="?",
        default=None,
        help="Optional: Build only the specified target image and its "
        "dependencies. If not specified, all images are built.",
    )
    parser.add_argument(
        "--print-tag",
        action="store_true",
        help="If specified, print the generated tag for the target_image and "
        "exit. Requires target_image to be specified.",
    )
    parser.add_argument(
        "--config",
        default="devkit.json",
        help="Path to the devkit.json file.",
    )
    parser.add_argument(
        "--search-path",
        action="append",
        required=True,
        help="Search path for Dockerfiles.",
    )

    args = parser.parse_args()
    load_config(args.config)

    image_configs_map = load_image_configs(args.search_path)

    print_tag_mode = args.print_tag
    target_image = args.target_image
    target_image_for_tag_print = None

    all_image_names = list(image_configs_map.keys())

    if print_tag_mode:
        if not target_image:
            print("Error: --print-tag requires a target_image to be specified.")
            sys.exit(1)
        target_image_for_tag_print = target_image
        if target_image_for_tag_print not in all_image_names:
            print(
                f"Error: Target image '{target_image_for_tag_print}' for "
                "--print-tag is not a valid image name."
            )
            sys.exit(1)
    elif target_image and target_image not in all_image_names:
        print(
            f"Error: Specified target image '{target_image}' is not a valid "
            "image name."
        )
        print(f"Choose from: {', '.join(all_image_names)}")
        sys.exit(1)

    images_to_process = []
    if target_image:
        images_to_process = get_dependency_subgraph(target_image, image_configs_map)
        print(
            f"Processing Docker image '{target_image}' and its "
            f"dependencies: {', '.join(images_to_process)}..."
        )
    else:
        # If no target image, build all images in a valid topological order
        full_graph = {
            name: set(conf["deps"].values()) for name, conf in image_configs_map.items()
        }
        try:
            ts = graphlib.TopologicalSorter(full_graph)
            images_to_process = list(ts.static_order())
            print("Processing all Docker images...")
        except graphlib.CycleError as e:
            print(f"Error: Cycle detected in image dependencies: {e}")
            sys.exit(1)

    generated_tags: Dict[str, str] = {}

    for image_name in images_to_process:
        image_conf = image_configs_map[image_name]
        dependencies = image_conf["deps"]

        process_image(
            image_name,
            dependencies,
            generated_tags,
            print_tag_mode,
            target_image_for_tag_print,
            args.search_path,
        )

    if print_tag_mode:
        # Fallback: If loop finishes in print_tag_mode, target wasn't found or
        # logic error. This path should ideally not be reached if validations
        # are correct.
        print(
            f"Error: Target image '{target_image_for_tag_print}' for "
            "--print-tag was not processed as expected."
        )
        sys.exit(1)
    else:
        if target_image:
            print(
                f"Targeted Docker image '{target_image}' and its dependencies "
                "processed successfully."
            )
        else:
            print("All Docker images processed successfully.")


if __name__ == "__main__":  # pragma: no cover
    main()
