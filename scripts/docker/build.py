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
from typing import List, Dict, Optional, TypedDict, Any
import json
import graphlib
import logging
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = ""
ARCH = "amd64"
EXTRA_PACKAGES_MAP: Dict[str, List[str]] = {}
EXTRA_KEYS_MAP: Dict[str, List[str]] = {}
EXTRA_REPOSITORIES_MAP: Dict[str, List[str]] = {}


CONFIG_SCHEMA = {
    "type": dict,
    "properties": {
        "docker": {
            "type": dict,
            "properties": {
                "registry": {
                    "type": dict,
                    "properties": {
                        "host": {"type": str},
                        "project": {"type": str},
                        "repository": {"type": str},
                    },
                    "additional_properties": False,
                },
                "run": {"type": list},
                "images": {
                    "type": dict,
                    "additional_properties": {
                        "type": dict,
                        "properties": {
                            "packages": {
                                "type": dict,
                                "additional_properties": {"type": str},
                            },
                            "keys": {
                                "type": dict,
                                "additional_properties": {"type": str},
                            },
                            "repositories": {
                                "type": dict,
                                "additional_properties": {"type": str},
                            },
                        },
                        "additional_properties": False,
                    },
                },
            },
            "additional_properties": False,
        }
    },
    "additional_properties": False,
}


def validate_config(data: Any, schema: Dict[str, Any], path: str = "") -> None:
    """Validates the config against the schema."""
    expected_type = schema.get("type")
    if expected_type and not isinstance(data, expected_type):
        raise ValueError(
            f"Invalid type at '{path}'. Expected {expected_type.__name__}, "
            f"got {type(data).__name__}."
        )

    if isinstance(data, dict):
        properties = schema.get("properties", {})
        additional_properties = schema.get("additional_properties", True)

        if additional_properties is False:
            extra_keys = set(data.keys()) - set(properties.keys())
            if extra_keys:
                raise ValueError(
                    f"Unexpected fields at '{path}': {', '.join(sorted(extra_keys))}"
                )

        for key, prop_schema in properties.items():
            if key in data:
                validate_config(
                    data[key],
                    prop_schema,
                    path=f"{path}.{key}" if path else key,
                )

        if isinstance(additional_properties, dict):
            for key, value in data.items():
                if key not in properties:
                    validate_config(
                        value,
                        additional_properties,
                        path=f"{path}.{key}" if path else key,
                    )


def check_docker_installed(log_file: Optional[Path]) -> None:
    """Checks if Docker is installed and available."""
    try:
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
        )
        logging.info("Docker is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        error_msg = "Docker is not installed or not in PATH. Please install Docker."
        logging.error(error_msg)
        if log_file:
            print(f"ERROR: {error_msg}", file=sys.stderr)
        sys.exit(1)


def check_docker_buildx_installed(log_file: Optional[Path]) -> None:
    """Checks if Docker Buildx is installed and available."""
    try:
        subprocess.run(
            ["docker", "buildx", "version"],
            check=True,
            capture_output=True,
        )
        logging.info("Docker Buildx is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        error_msg = (
            "Docker Buildx is not installed or not enabled. "
            "Please install/enable Docker Buildx."
        )
        logging.error(error_msg)
        if log_file:
            print(f"ERROR: {error_msg}", file=sys.stderr)
        sys.exit(1)


def _load_registry_config(config: Dict[str, Any]) -> None:
    """Loads the registry config from the docker config."""
    global REPO
    if "registry" in config["docker"]:
        registry = config["docker"]["registry"]
        if "host" in registry and "project" in registry and "repository" in registry:
            h = registry["host"]
            p = registry["project"]
            r = registry["repository"]
            if h and p and r:
                REPO = f"{h}/{p}/{r}"


def _load_images_config(config: Dict[str, Any]) -> None:
    """Loads the images config from the docker config."""
    if "images" in config["docker"]:
        for img, settings in config["docker"]["images"].items():
            if "packages" in settings:
                packages = []
                for k, v in settings["packages"].items():
                    if not v:
                        logging.error(
                            "Package %s in image %s has an empty version. "
                            "Please specify a version or use '*'.",
                            k,
                            img,
                        )
                        sys.exit(1)
                    packages.append(f"{k}={v}")
                EXTRA_PACKAGES_MAP[img] = packages
            if "keys" in settings:
                keys = []
                for k, v in settings["keys"].items():
                    keys.append(f"{k}={v}")
                EXTRA_KEYS_MAP[img] = keys
            if "repositories" in settings:
                repos = []
                for k, v in settings["repositories"].items():
                    repos.append(f"{k}={v}")
                EXTRA_REPOSITORIES_MAP[img] = repos


def load_config(config_path: str) -> None:
    """Loads the devkit.json config file."""
    if not os.path.exists(config_path):
        logging.info("devkit.json config file not found: %s", config_path)
        return
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
            validate_config(config, CONFIG_SCHEMA)
            if "docker" in config:
                _load_registry_config(config)
                _load_images_config(config)
        except (json.JSONDecodeError, ValueError) as e:
            logging.error("Could not load %s: %s", config_path, e)
            sys.exit(1)


class ImageConfig(TypedDict):
    deps: Dict[str, str]
    local: Optional[bool]


ImageConfigsMap = Dict[str, ImageConfig]


def load_image_configs(search_paths: List[str]) -> ImageConfigsMap:
    """Loads all deps.json files from the search paths."""
    all_configs: ImageConfigsMap = {}
    for path in search_paths:
        deps_file = os.path.join(path, "deps.json")
        if os.path.exists(deps_file):
            logging.info("Loading image configs from %s", deps_file)
            with open(deps_file, "r", encoding="utf-8") as f:
                try:
                    configs = json.load(f)
                    if isinstance(configs, dict):
                        all_configs.update(configs)
                    else:
                        logging.warning(
                            "%s does not contain a dict of configs.", deps_file
                        )
                except json.JSONDecodeError as e:
                    logging.error("Could not decode %s: %s", deps_file, e)
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
    local_image_mode: Optional[bool],
) -> None:
    """
    If repo is not defined or local_image_mode is true:
        Checks if a Docker image exists and if not, it builds it.
    Otherwise:
        Checks if a Docker image exists, pulls it if available in registry,
        or builds and pushes it otherwise.
    Args:
        tag: The full tag of the image.
        dockerfile_path: Absolute path to the Dockerfile.
        build_args_list: A list of build arguments,
          e.g., ["ARG_NAME1", "VALUE1", "ARG_NAME2", "VALUE2"].
        context_path: The Docker build context path.
        local_image_mode: The flag that controls whether the image should be local-only,
          i.e. if true, the image won't be pulled from and pushed to remote registry.
    """
    try:
        if check_if_image_exists_locally(tag):
            return
        if not REPO or local_image_mode:
            if not REPO:
                logging.warning("Docker registry is not defined.")
            build_image(tag, dockerfile_path, build_args_list, context_path)
            return
        if check_if_image_exists_in_remote_registry(tag):
            pull_image_from_registry(tag)
            return
        build_image(tag, dockerfile_path, build_args_list, context_path)
        push_image_to_registry(tag)

    except subprocess.CalledProcessError as e:
        print(" [FAILED]", file=sys.stderr)
        logging.error("Error during Docker operation for %s:", tag)
        logging.error("Command: %s", " ".join(e.cmd))
        if e.stdout:
            logging.error("Stdout: %s", e.stdout.strip())
        if e.stderr:
            logging.error("Stderr: %s", e.stderr.strip())
        sys.exit(e.returncode if e.returncode != 0 else 1)
    except FileNotFoundError:  # pragma: no cover
        logging.error(
            "Docker command not found. "
            "Please ensure Docker is installed and in PATH.",
        )
        sys.exit(1)


def check_if_image_exists_locally(tag: str) -> bool:
    """
    Check if docker image exists locally.

    Args:
        tag: The full tag of the image.

    Returns:
        bool: True if image exists, False otherwise.
    """
    logging.info("Checking for local image: %s", tag)
    inspect_cmd = ["docker", "image", "inspect", tag]
    inspect_result = subprocess.run(
        inspect_cmd, capture_output=True, text=True, check=False
    )

    if inspect_result.returncode == 0:
        logging.info("Image %s already exists locally.", tag)
        return True
    logging.info("Image %s not found locally.", tag)
    return False


def build_image(
    tag: str, dockerfile_path: str, build_args_list: List[str], context_path: str
) -> None:
    """
    Builds docker image.

    Args:
        tag: The full tag of the image.
        dockerfile_path: Absolute path to the Dockerfile.
        build_args_list: A list of build arguments,
          e.g., ["ARG_NAME1", "VALUE1", "ARG_NAME2", "VALUE2"].
        context_path: The Docker build context path.

    Returns:
        None
    """
    print(f"Building image: {tag}...", file=sys.stderr, end="", flush=True)

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

    logging.info("Executing build: %s", " ".join(docker_build_cmd))
    process = subprocess.run(
        docker_build_cmd, check=True, text=True, capture_output=True
    )
    print(" [OK]", file=sys.stderr)
    if process.stdout:
        logging.info(process.stdout.strip())
    if process.stderr:
        logging.warning(process.stderr.strip())
    logging.info("Image %s built successfully.", tag)


def check_if_image_exists_in_remote_registry(tag: str) -> bool:
    """
    Checks if image exists in remote docker registry.

    Args:
        tag: The full tag of the image.

    Returns:
        bool: True if image exists remotely, False otherwise
    """
    logging.info("Checking for remote image manifest: %s", tag)
    manifest_inspect_cmd = ["docker", "manifest", "inspect", tag]
    manifest_result = subprocess.run(
        manifest_inspect_cmd, capture_output=True, text=True, check=False
    )

    if manifest_result.returncode == 0:
        logging.info("Image %s found in remote registry.", tag)
        return True
    logging.info("Image %s not found in remote registry.", tag)
    return False


def pull_image_from_registry(tag: str) -> None:
    """
    Pulls image from remote docker registry.

    Args:
        tag: The full tag of the image.

    Returns:
        None
    """
    print(f"Pulling image: {tag}...", file=sys.stderr, end="", flush=True)
    pull_cmd = ["docker", "pull", tag]
    process = subprocess.run(pull_cmd, check=True, text=True, capture_output=True)
    print(" [OK]", file=sys.stderr)
    if process.stdout:
        logging.info(process.stdout.strip())
    if process.stderr:
        logging.warning(process.stderr.strip())
    logging.info("Image %s pulled successfully.", tag)


def push_image_to_registry(tag: str) -> None:
    """
    Push image to remote docker registry.

    Args:
        tag: The full tag of the image.

    Returns:
        None
    """
    logging.info("Pushing image %s...", tag)
    print(f"Pushing image: {tag}...", file=sys.stderr, end="", flush=True)
    push_cmd = ["docker", "push", tag]
    push_result = subprocess.run(push_cmd, check=False, text=True, capture_output=True)
    if push_result.returncode == 0:
        print(" [OK]", file=sys.stderr)
        if push_result.stdout:
            logging.info(push_result.stdout.strip())
        if push_result.stderr:
            logging.warning(push_result.stderr.strip())
        logging.info("Image %s pushed successfully.", tag)
    else:
        print(" [FAILED]", file=sys.stderr)
        logging.warning("Failed to push image %s. Continuing with local image.", tag)
        if push_result.stderr:
            logging.warning("Details: %s", push_result.stderr.strip())


def process_image(
    image_name: str,
    dependencies: Dict[str, str],
    generated_tags: Dict[str, str],
    print_tag_mode: bool,
    target_image_for_tag_print: Optional[str],
    search_paths: List[str],
    local_image_mode: Optional[bool],
) -> Optional[str]:
    """
    Processes a single image: calculates its tag, builds/pulls/pushes it,
    and optionally prints the tag.
    """
    logging.info("=== Processing: %s ===", image_name)
    dockerfile_name = f"{image_name}.Dockerfile"
    dockerfile_path = None

    for path in search_paths:
        potential_path = os.path.join(path, dockerfile_name)
        if os.path.exists(potential_path):
            dockerfile_path = potential_path
            break

    if not dockerfile_path:
        logging.error(
            "Dockerfile %s not found for image '%s' in any of the search paths: %s.",
            dockerfile_name,
            image_name,
            search_paths,
        )
        sys.exit(1)

    dockerfile_path = os.path.realpath(dockerfile_path)

    build_args_for_manage = []  # For calling manage_image: [ARG_NAME, ARG_VALUE, ...]
    build_args_for_sha_calc = []  # For SHA calculation: ["ARG_NAME=VALUE", ...]

    for arg_name, dep_image_name in dependencies.items():
        if dep_image_name not in generated_tags:  # pragma: no cover
            logging.error(
                "Dependency tag for '%s' (needed by '%s' as build arg '%s') not found.",
                dep_image_name,
                image_name,
                arg_name,
            )
            logging.error(
                "Ensure images are in the correct build order and all "
                "dependencies are defined correctly."
            )
            sys.exit(1)

        dep_tag = generated_tags[dep_image_name]
        build_args_for_manage.extend([arg_name, dep_tag])
        build_args_for_sha_calc.append(f"{arg_name}={dep_tag}")
        logging.info(
            "Build arg for %s: %s=%s (Tag: %s)",
            image_name,
            arg_name,
            dep_image_name,
            dep_tag,
        )

    extra_pkgs = EXTRA_PACKAGES_MAP.get(image_name, [])
    if extra_pkgs:
        extra_pkgs_str = " ".join(extra_pkgs)
        build_args_for_manage.extend(["EXTRA_PACKAGES", extra_pkgs_str])
        build_args_for_sha_calc.append(f"EXTRA_PACKAGES={extra_pkgs_str}")
        logging.info(
            "Build arg for %s: EXTRA_PACKAGES=%s",
            image_name,
            extra_pkgs_str,
        )

    extra_keys = EXTRA_KEYS_MAP.get(image_name, [])
    if extra_keys:
        extra_keys_str = " ".join(extra_keys)
        build_args_for_manage.extend(["EXTRA_KEYS", extra_keys_str])
        build_args_for_sha_calc.append(f"EXTRA_KEYS={extra_keys_str}")
        logging.info(
            "Build arg for %s: EXTRA_KEYS=%s",
            image_name,
            extra_keys_str,
        )

    extra_repos = EXTRA_REPOSITORIES_MAP.get(image_name, [])
    if extra_repos:
        extra_repos_str = " ".join(extra_repos)
        build_args_for_manage.extend(["EXTRA_REPOSITORIES", extra_repos_str])
        build_args_for_sha_calc.append(f"EXTRA_REPOSITORIES={extra_repos_str}")
        logging.info(
            "Build arg for %s: EXTRA_REPOSITORIES=%s",
            image_name,
            extra_repos_str,
        )

    build_args_for_sha_calc.sort()

    try:
        current_sha = calculate_sha256(dockerfile_path, build_args_for_sha_calc)
    # Should be caught by os.path.exists, but defensive.
    except FileNotFoundError:  # pragma: no cover
        logging.error(
            "Dockerfile %s disappeared before SHA calculation for image %s.",
            dockerfile_path,
            image_name,
        )
        sys.exit(1)

    sha_info_str = (
        f"SHA for {dockerfile_path} (Content + Sorted Build Args "
        f"[{', '.join(build_args_for_sha_calc)}]): {current_sha}"
    )
    logging.info(sha_info_str)

    current_tag = get_image_tag(image_name, current_sha)
    logging.info("Tag for %s: %s", image_name, current_tag)
    generated_tags[image_name] = current_tag

    context_path = os.path.dirname(dockerfile_path)
    manage_docker_image(
        current_tag,
        dockerfile_path,
        build_args_for_manage,
        context_path,
        local_image_mode,
    )

    if print_tag_mode:
        if image_name == target_image_for_tag_print:
            print(current_tag)
            sys.exit(0)
    else:
        # manage_docker_image handles its own print and sys.exit calls on error.
        # If it returns, it was successful.
        logging.info(
            "=== Finished processing: %s ===",
            image_name,
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
        return []  # pragma: no cover

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
        logging.error("Cycle detected in dependencies for %s: %s", target_image_name, e)
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
        required=True,
        help="Path to the config file.",
    )
    parser.add_argument(
        "--search-path",
        action="append",
        required=True,
        help="Search path for Dockerfiles.",
    )
    parser.add_argument(
        "--log-file",
        help="Path to a file for logging. If not specified, logs to stderr.",
        type=Path,
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s]: %(message)s",
        filename=args.log_file,
        filemode="a" if args.log_file else "w",
    )

    check_docker_installed(args.log_file)
    check_docker_buildx_installed(args.log_file)

    load_config(args.config)

    image_configs_map = load_image_configs(args.search_path)

    print_tag_mode = args.print_tag
    target_image = args.target_image
    target_image_for_tag_print = None

    all_image_names = list(image_configs_map.keys())

    if print_tag_mode:
        if not target_image:
            logging.error("--print-tag requires a target_image to be specified.")
            sys.exit(1)
        target_image_for_tag_print = target_image
        if target_image_for_tag_print not in all_image_names:
            logging.error(
                "Target image '%s' for --print-tag is not a valid image name.",
                target_image_for_tag_print,
            )
            sys.exit(1)
    elif target_image and target_image not in all_image_names:
        logging.error(
            "Specified target image '%s' is not a valid image name.",
            target_image,
        )
        logging.error("Choose from: %s", ", ".join(all_image_names))
        sys.exit(1)

    images_to_process = []
    if target_image:
        images_to_process = get_dependency_subgraph(target_image, image_configs_map)
        logging.info(
            "Processing Docker image '%s' and its dependencies: %s...",
            target_image,
            ", ".join(images_to_process),
        )
    else:
        # If no target image, build all images in a valid topological order
        full_graph = {
            name: set(conf["deps"].values()) for name, conf in image_configs_map.items()
        }
        try:
            ts = graphlib.TopologicalSorter(full_graph)
            images_to_process = list(ts.static_order())
            logging.info("Processing all Docker images...")
        except graphlib.CycleError as e:
            logging.error("Cycle detected in image dependencies: %s", e)
            sys.exit(1)

    generated_tags: Dict[str, str] = {}

    for image_name in images_to_process:
        image_conf = image_configs_map[image_name]
        dependencies = image_conf["deps"]
        local_image_mode = image_conf["local"] if "local" in image_conf else None

        process_image(
            image_name,
            dependencies,
            generated_tags,
            print_tag_mode,
            target_image_for_tag_print,
            args.search_path,
            local_image_mode,
        )

    if print_tag_mode:  # pragma: no cover
        # Fallback: If loop finishes in print_tag_mode, target wasn't found or
        # logic error. This path should ideally not be reached if validations
        # are correct.
        logging.error(
            "Target image '%s' for --print-tag was not processed as expected.",
            target_image_for_tag_print,
        )
        sys.exit(1)
    else:
        if target_image:
            logging.info(
                "Targeted Docker image '%s' and its dependencies processed successfully.",
                target_image,
            )
        else:
            logging.info("All Docker images processed successfully.")


if __name__ == "__main__":  # pragma: no cover
    main()
