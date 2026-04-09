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

from collections.abc import Mapping, Sequence
import argparse
import hashlib
import os
import subprocess
import sys
from typing import Any, Optional, TypedDict
import json
import graphlib
import logging
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# Workaround for CI when uv is used. uv may install a newer Python version
# (e.g. 3.12+) which removes the 'imp' module used by older gcloud versions.
# If gcloud is triggered by a docker credential helper, it may run using the
# uv Python environment and fail. Setting CLOUDSDK_PYTHON to the system python
# ensures gcloud uses a compatible version.
def ensure_cloudsdk_python_is_set() -> None:
    if "CLOUDSDK_PYTHON" not in os.environ:
        for candidate in ["/usr/bin/python3", "/usr/bin/python"]:
            if os.path.exists(candidate):
                os.environ["CLOUDSDK_PYTHON"] = candidate
                break


ensure_cloudsdk_python_is_set()


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
                        "namespace": {"type": str},
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


def validate_config(data: Any, schema: Mapping[str, Any], path: str = "") -> None:
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


def parse_registry_config(config: Mapping[str, Any]) -> tuple[str, str]:
    """
    Extracts the repository and namespace from the docker configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        A tuple containing (repo, namespace).
    """
    repo = ""
    namespace = "devkit"
    if "docker" in config:
        docker_config = config["docker"]
        if "registry" in docker_config:
            registry = docker_config["registry"]
            if (
                "host" in registry
                and "project" in registry
                and "repository" in registry
            ):
                host = registry["host"]
                project = registry["project"]
                repository = registry["repository"]
                if host and project and repository:
                    repo = f"{host}/{project}/{repository}"
            if "namespace" in registry and registry["namespace"]:
                namespace = f"devkit/{registry['namespace']}"
    return repo, namespace


def get_image_prefix(config_path: Path) -> str:
    """
    Returns the Docker image prefix (repo/namespace/) from the configuration file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        The image prefix string.
    """
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                repo, namespace = parse_registry_config(config)
                if repo:
                    return f"{repo}/{namespace}"
                return f"{namespace}"
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return "devkit"


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


class ImageConfig(TypedDict):
    deps: dict[str, str]
    local: Optional[bool]


ImageConfigsMap = dict[str, ImageConfig]


def load_image_configs(search_paths: Sequence[Path]) -> ImageConfigsMap:
    """Loads all deps.json files from the search paths."""
    all_configs: ImageConfigsMap = {}
    for path in search_paths:
        deps_file = path / "deps.json"
        if deps_file.exists():
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


def calculate_sha256(dockerfile_path: str, sorted_build_args: Sequence[str]) -> str:
    """
    Calculates SHA256 hash based on Dockerfile content and sorted build arguments.
    """
    hasher = hashlib.sha256()

    with open(dockerfile_path, "rb") as f:
        hasher.update(f.read())

    for arg_val_pair in sorted_build_args:
        hasher.update(arg_val_pair.encode("utf-8"))

    return hasher.hexdigest()


def get_dependency_subgraph(
    target_image_names: Sequence[str],
    image_configs_map: Mapping[str, ImageConfig],
) -> Sequence[str]:
    """Finds all dependencies for target images and returns them topologically sorted."""
    full_graph = {
        name: set(conf["deps"].values()) for name, conf in image_configs_map.items()
    }

    nodes_to_visit = set(target_image_names)
    visited_nodes = set()
    while nodes_to_visit:
        current_node = nodes_to_visit.pop()
        if current_node not in visited_nodes:
            visited_nodes.add(current_node)
            if current_node in full_graph:
                nodes_to_visit.update(full_graph[current_node])

    subgraph = {node: full_graph[node] for node in visited_nodes if node in full_graph}

    try:
        ts = graphlib.TopologicalSorter(subgraph)
        return list(ts.static_order())
    except Exception as e:
        logging.error("Cycle detected in dependencies: %s", e)
        sys.exit(1)


class DockerBuilder:
    """Manages Docker image building and tag calculation."""

    def __init__(self, config_path: Path, search_paths: Sequence[Path]):
        self.config_path = config_path
        self.search_paths = search_paths
        self.repo = ""
        self.namespace = "devkit"
        self.arch = "amd64"
        self.extra_packages_map: dict[str, list[str]] = {}
        self.extra_keys_map: dict[str, list[str]] = {}
        self.extra_repositories_map: dict[str, list[str]] = {}
        self.image_configs_map: ImageConfigsMap = {}
        self.generated_tags: dict[str, str] = {}

        self._load_config()
        self.image_configs_map = load_image_configs(self.search_paths)

    def _load_config(self) -> None:
        """Loads the devkit.json config file."""
        if not self.config_path.exists():
            logging.info("devkit.json config file not found: %s", self.config_path)
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
                validate_config(config, CONFIG_SCHEMA)
                if "docker" in config:
                    self._load_registry_config(config)
                    self._load_images_config(config)
            except (json.JSONDecodeError, ValueError) as e:
                logging.error("Could not load %s: %s", self.config_path, e)
                sys.exit(1)

    def _load_registry_config(self, config: Mapping[str, Any]) -> None:
        """Loads the registry config from the docker config."""
        self.repo, self.namespace = parse_registry_config(config)

    def _load_images_config(self, config: Mapping[str, Any]) -> None:
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
                    self.extra_packages_map[img] = packages
                if "keys" in settings:
                    keys = []
                    for k, v in settings["keys"].items():
                        keys.append(f"{k}={v}")
                    self.extra_keys_map[img] = keys
                if "repositories" in settings:
                    repos = []
                    for k, v in settings["repositories"].items():
                        repos.append(f"{k}={v}")
                    self.extra_repositories_map[img] = repos

    def get_image_tag(self, image_name: str, sha: str) -> str:
        """Constructs the full image tag."""
        image_path = f"{self.namespace}/{image_name}"
        tag_suffix = f"{self.arch}-{sha}"
        if self.repo:
            return f"{self.repo}/{image_path}:{tag_suffix}"
        return f"{image_path}:{tag_suffix}"

    def get_build_order(
        self, target_images: Optional[Sequence[str]] = None
    ) -> Sequence[str]:
        """Determines the topologically sorted build order for all or targeted images."""
        if target_images:
            images_to_process = self.get_dependency_subgraph(target_images)
            logging.info(
                "Processing Docker images %s and their dependencies: %s...",
                ", ".join(target_images),
                ", ".join(images_to_process),
            )
            return images_to_process

        full_graph = {
            name: set(conf["deps"].values())
            for name, conf in self.image_configs_map.items()
        }
        try:
            ts = graphlib.TopologicalSorter(full_graph)
            images_to_process = list(ts.static_order())
            logging.info("Processing all Docker images...")
            return images_to_process
        except Exception as e:
            logging.error("Cycle detected in image dependencies: %s", e)
            sys.exit(1)

    def calculate_tags(
        self, target_images: Optional[Sequence[str]] = None
    ) -> Sequence[str]:
        """Calculates tags for images in topological order."""
        images_to_process = self.get_build_order(target_images)

        for image_name in images_to_process:
            self.calculate_tag_for_image(image_name)

        return [self.generated_tags[name] for name in images_to_process]

    def calculate_tag_for_image(self, image_name: str) -> str:
        """Calculates the tag for a single image, recursively handling dependencies."""
        if image_name in self.generated_tags:
            return self.generated_tags[image_name]

        logging.info("=== Calculating tag for: %s ===", image_name)
        image_conf = self.image_configs_map[image_name]
        dependencies = image_conf["deps"]

        dockerfile_name = f"{image_name}.Dockerfile"
        dockerfile_path = None

        for path in self.search_paths:
            potential_path = os.path.join(path, dockerfile_name)
            if os.path.exists(potential_path):
                dockerfile_path = potential_path
                break

        if not dockerfile_path:
            logging.error(
                "Dockerfile %s not found for image '%s' in any of the search paths: %s.",
                dockerfile_name,
                image_name,
                self.search_paths,
            )
            sys.exit(1)

        dockerfile_path = os.path.realpath(dockerfile_path)
        build_args_for_sha_calc = []

        for arg_name, dep_image_name in dependencies.items():
            dep_tag = self.calculate_tag_for_image(dep_image_name)
            build_args_for_sha_calc.append(f"{arg_name}={dep_tag}")

        for map_attr, arg_name in [
            ("extra_packages_map", "EXTRA_PACKAGES"),
            ("extra_keys_map", "EXTRA_KEYS"),
            ("extra_repositories_map", "EXTRA_REPOSITORIES"),
        ]:
            val = getattr(self, map_attr).get(image_name, [])
            if val:
                val_str = " ".join(val)
                build_args_for_sha_calc.append(f"{arg_name}={val_str}")

        build_args_for_sha_calc.sort()
        sha = calculate_sha256(dockerfile_path, build_args_for_sha_calc)
        tag = self.get_image_tag(image_name, sha)
        self.generated_tags[image_name] = tag
        logging.info("Tag for %s: %s", image_name, tag)
        return tag

    def get_dependency_subgraph(
        self, target_image_names: Sequence[str]
    ) -> Sequence[str]:
        """
        Finds all dependencies for target images and returns them topologically sorted.
        """
        return get_dependency_subgraph(target_image_names, self.image_configs_map)

    def build_images(
        self,
        target_images: Sequence[str],
        print_tag_mode: bool,
        no_cache: bool,
        local_flag: bool,
    ) -> None:
        """Builds, pulls, or pushes images based on calculated tags."""
        images_to_process = self.get_build_order(
            target_images if target_images else None
        )

        target_image_for_tag_print = target_images[0] if print_tag_mode else None

        for image_name in images_to_process:
            tag = self.calculate_tag_for_image(image_name)
            image_conf = self.image_configs_map[image_name]
            local_image_mode = local_flag or image_conf.get("local", False)

            # We need the dockerfile_path for building.
            # calculate_tag_for_image already verified it exists.
            dockerfile_name = f"{image_name}.Dockerfile"
            dockerfile_path = None
            for path in self.search_paths:
                potential_path = os.path.join(path, dockerfile_name)
                if os.path.exists(potential_path):
                    dockerfile_path = potential_path
                    break

            if not dockerfile_path:  # pragma: no cover
                logging.error("Dockerfile %s not found.", dockerfile_name)
                sys.exit(1)

            dockerfile_path = os.path.realpath(dockerfile_path)
            context_path = os.path.dirname(dockerfile_path)

            build_args_for_manage = []
            dependencies = image_conf["deps"]
            for arg_name, dep_image_name in dependencies.items():
                build_args_for_manage.extend(
                    [arg_name, self.generated_tags[dep_image_name]]
                )

            for map_attr, arg_name in [
                ("extra_packages_map", "EXTRA_PACKAGES"),
                ("extra_keys_map", "EXTRA_KEYS"),
                ("extra_repositories_map", "EXTRA_REPOSITORIES"),
            ]:
                val = getattr(self, map_attr).get(image_name, [])
                if val:
                    build_args_for_manage.extend([arg_name, " ".join(val)])

            manage_docker_image(
                tag,
                dockerfile_path,
                build_args_for_manage,
                context_path,
                local_image_mode,
                no_cache,
                self.repo,
            )

            if print_tag_mode and image_name == target_image_for_tag_print:
                print(tag)
                sys.exit(0)

        if not print_tag_mode:
            if target_images:
                logging.info(
                    "Targeted Docker images %s and dependencies processed successfully.",
                    ", ".join(target_images),
                )
            else:
                logging.info("All Docker images processed successfully.")


def get_all_docker_image_tags(
    config_path: Path,
    search_paths: Sequence[Path],
    target_images: Optional[Sequence[str]] = None,
) -> Sequence[str]:
    """Returns full docker image tags list for all or targeted images."""
    builder = DockerBuilder(config_path, search_paths)
    return builder.calculate_tags(target_images)


def manage_docker_image(
    tag: str,
    dockerfile_path: str,
    build_args_list: Sequence[str],
    context_path: str,
    local_image_mode: Optional[bool],
    no_cache: bool = False,
    repo: str = "",
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
        no_cache: If true, the image will be rebuilt even if it already exists locally.
        repo: The Docker registry path.
    """
    try:
        if not no_cache and check_if_image_exists_locally(tag):
            return
        if not repo or local_image_mode:
            if not repo:
                logging.warning("Docker registry is not defined.")
            build_image(tag, dockerfile_path, build_args_list, context_path, no_cache)
            return
        if not no_cache and check_if_image_exists_in_remote_registry(tag):
            pull_image_from_registry(tag)
            return
        build_image(tag, dockerfile_path, build_args_list, context_path, no_cache)
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
    tag: str,
    dockerfile_path: str,
    build_args_list: Sequence[str],
    context_path: str,
    no_cache: bool = False,
) -> None:
    """
    Builds docker image.

    Args:
        tag: The full tag of the image.
        dockerfile_path: Absolute path to the Dockerfile.
        build_args_list: A list of build arguments,
          e.g., ["ARG_NAME1", "VALUE1", "ARG_NAME2", "VALUE2"].
        context_path: The Docker build context path.
        no_cache: If true, builds with --no-cache.

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

    if no_cache:
        docker_build_cmd.append("--no-cache")

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Docker images with content-addressable tagging.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "target_images",
        nargs="*",
        default=[],
        help="Optional: Build only the specified target images and their "
        "dependencies. If not specified, all images are built.",
    )
    parser.add_argument(
        "--print-tag",
        action="store_true",
        help="If specified, print the generated tag for the target_image and "
        "exit. Requires exactly one target_image to be specified.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the config file.",
        type=Path,
    )
    parser.add_argument(
        "--search-path",
        action="append",
        required=True,
        help="Search path for Dockerfiles.",
        type=Path,
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="If specified, build and manage Docker images locally only, "
        "without pulling from or pushing to the remote registry.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="If specified, the image will be rebuilt, "
        "even if it is already built by docker.",
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

    builder = DockerBuilder(args.config, args.search_path)

    all_image_names = list(builder.image_configs_map.keys())

    if args.print_tag:
        if len(args.target_images) != 1:
            logging.error(
                "--print-tag requires exactly one target_image to be specified."
            )
            sys.exit(1)
        target_image_for_tag_print = args.target_images[0]
        if target_image_for_tag_print not in all_image_names:
            logging.error(
                "Target image '%s' for --print-tag is not a valid image name.",
                target_image_for_tag_print,
            )
            sys.exit(1)
    else:
        for ti in args.target_images:
            if ti not in all_image_names:
                logging.error(
                    "Specified target image '%s' is not a valid image name.",
                    ti,
                )
                logging.error("Choose from: %s", ", ".join(all_image_names))
                sys.exit(1)

    builder.build_images(args.target_images, args.print_tag, args.no_cache, args.local)


if __name__ == "__main__":  # pragma: no cover
    main()
