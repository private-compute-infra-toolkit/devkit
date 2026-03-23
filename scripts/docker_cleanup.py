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
This script provides functionality for cleaning up old docker images in the background.
"""

import argparse
import logging
import re
import subprocess
from pathlib import Path
from threading import Event, Thread
from collections.abc import Sequence
from docker.build import get_all_docker_image_tags, get_image_prefix

INITIAL_CLEANUP_DELAY_SECONDS = 5.0
CLEANUP_INTERVAL_SECONDS = 2.0
CLEANUP_BATCH_SIZE = 4
CLEANUP_THRESHOLD_DAYS = 7

ALLOWED_IMAGE_NAMES = {
    # DO NOT REMOVE OLD ENTRIES.
    # We still need to clean images that might have been removed from the
    # repository, but are still present in the registry.
    "build-env",
    "build-env-debian",
    "build-env-rockylinux",
    "clion-ide",
    "dev-env",
    "gcloud-env",
    "goland-ide",
    "ide-env",
    "intellij-ide",
    "nitro-cli-linux6",
    "pycharm-ide",
    "tool-env",
    "vscode-ide",
    "vscode-server",
}

# Regex to match image formats like:
# [registry/][project/][repo/]devkit[/namespace]/name:arch-hash.
# It requires 'devkit' to be present as a component of the path.
# The hash must be a 64-character hex string (SHA256).
IMAGE_PATTERN = re.compile(
    r"^(?:.*/)?devkit(?:/.*)?/([^/:]+):([a-zA-Z0-9_]+)-([a-f0-9]{64})$"
)


def get_ignored_images(
    config_path: Path, search_paths: Sequence[Path]
) -> Sequence[str]:
    """
    Calculates the list of Docker image tags that should be ignored during cleanup.
    """
    try:
        ignored_images = list(get_all_docker_image_tags(config_path, search_paths))
        logging.info(
            "Determined %d images to ignore during cleanup.", len(ignored_images)
        )
        return ignored_images
    except Exception as e:
        logging.warning("Failed to calculate ignored images for cleanup: %s", e)
        return []


def get_images(
    image_prefix: str, threshold_days: int = CLEANUP_THRESHOLD_DAYS
) -> Sequence[str]:
    """
    Returns a list of all Docker images matching the given repository+namespace prefix
    that are older than threshold_days.
    """
    threshold_hours = threshold_days * 24
    try:
        # Get matching images with repository and tag.
        result = subprocess.run(
            [
                "docker",
                "images",
                "--filter",
                f"reference={image_prefix}/*",
                "--filter",
                f"until={threshold_hours}h",
                "--format",
                "{{.Repository}}:{{.Tag}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.warning("Failed to list docker images: %s", e)
        return []


def filter_allowed_images(images: Sequence[str]) -> Sequence[str]:
    """
    Filters a list of Docker images, returning only those whose name
    is present in the allowlist and matches the <name>:<arch>-<hash> format.
    """
    allowed_images = []
    for img in images:
        match = IMAGE_PATTERN.match(img)
        if match:
            image_name = match.group(1)
            if image_name in ALLOWED_IMAGE_NAMES:
                allowed_images.append(img)
            else:
                logging.info("Skipping image %s as it is not in the allowlist.", img)
        else:
            logging.info(
                "Skipping image %s as it does not match the expected format.", img
            )
    return allowed_images


def get_images_to_cleanup(
    config_path: Path,
    search_paths: Sequence[Path],
    threshold_days: int = CLEANUP_THRESHOLD_DAYS,
) -> Sequence[str]:
    """
    Returns a list of Docker images that are candidates for cleanup.
    """
    image_prefix = get_image_prefix(config_path)
    all_images = get_images(image_prefix, threshold_days)

    if not all_images:
        logging.info("No images found for cleanup.")
        return []

    allowed_images = filter_allowed_images(all_images)

    if not allowed_images:
        logging.info("No allowed images found for cleanup.")
        return []

    ignored_images = get_ignored_images(config_path, search_paths)
    ignored_set = set(ignored_images)
    all_to_cleanup = [img for img in allowed_images if img not in ignored_set]

    if not all_to_cleanup:
        logging.info("All found images are in the ignore list. Nothing to clean up.")
        return []

    logging.info("Found %d images to clean up.", len(all_to_cleanup))
    return all_to_cleanup


def cleanup_images_batch(cancel_event: Event, images_to_cleanup: Sequence[str]) -> None:
    """
    Performs a single batch of docker image cleanup.
    """
    if not images_to_cleanup:
        return

    logging.info("Cleaning up %d images in this batch.", len(images_to_cleanup))
    for tag in images_to_cleanup:
        if cancel_event.is_set():
            return

        logging.info("Removing image: %s", tag)
        try:
            # We use Popen and poll to remain interruptible by the cancel_event.
            with subprocess.Popen(
                ["docker", "rmi", tag],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as proc:
                while proc.poll() is None:
                    if cancel_event.wait(timeout=0.1):
                        logging.info(
                            "Cleanup cancelled; exiting removal loop for %s", tag
                        )
                        proc.terminate()
                        return

                stdout, stderr = proc.communicate()
                if stdout:
                    for line in stdout.strip().splitlines():
                        logging.info("[docker rmi stdout]: %s", line)
                if stderr:
                    for line in stderr.strip().splitlines():
                        logging.warning("[docker rmi stderr]: %s", line)

                if proc.returncode != 0:
                    logging.warning(
                        "Failed to remove image %s (exit code %d)",
                        tag,
                        proc.returncode,
                    )
        except Exception as e:
            logging.warning("Error during image removal of %s: %s", tag, e)


def cleanup_images(
    cancel_event: Event,
    config_path: Path,
    search_paths: Sequence[Path],
    initial_delay: float = INITIAL_CLEANUP_DELAY_SECONDS,
    interval: float = CLEANUP_INTERVAL_SECONDS,
    batch_size: int = CLEANUP_BATCH_SIZE,
    threshold_days: int = CLEANUP_THRESHOLD_DAYS,
) -> None:
    """
    Cleans up docker images in a loop.

    Waits for an initial delay, calculates the list of Docker image cleanup
    candidates based on the provided configuration, and then enters a loop
    to perform cleanup batches until no more candidates need cleaning or
    the task is cancelled.
    """
    if cancel_event.wait(initial_delay):
        return

    all_to_cleanup = get_images_to_cleanup(config_path, search_paths, threshold_days)

    for i in range(0, len(all_to_cleanup), batch_size):
        batch = all_to_cleanup[i : i + batch_size]
        cleanup_images_batch(cancel_event, batch)

        if cancel_event.wait(interval):
            break


def start_background_cleanup(
    config_path: Path,
    search_paths: Sequence[Path],
    initial_delay: float = INITIAL_CLEANUP_DELAY_SECONDS,
    interval: float = CLEANUP_INTERVAL_SECONDS,
    batch_size: int = CLEANUP_BATCH_SIZE,
    threshold_days: int = CLEANUP_THRESHOLD_DAYS,
) -> tuple[Thread, Event]:
    """
    Starts the docker cleanup task in a background daemon thread.
    Returns the thread and the event used to cancel it.
    """
    cancel_event = Event()
    thread = Thread(
        target=cleanup_images,
        args=(
            cancel_event,
            config_path,
            search_paths,
            initial_delay,
            interval,
            batch_size,
            threshold_days,
        ),
        name="DockerCleanupThread",
        daemon=True,
    )
    thread.start()
    return thread, cancel_event


def main() -> None:
    """
    Manual entry point for docker image cleanup.
    """
    parser = argparse.ArgumentParser(
        description="Cleanup old docker images.",
        add_help=True,
    )
    parser.add_argument(
        "--devkit-log-file",
        help="Path to a file for logging. If not specified, logs to stderr.",
        type=Path,
    )
    parser.add_argument(
        "--config-path",
        help="Path to devkit.json.",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--search-path",
        help="Paths to search for images (e.g. project root / 'images').",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument(
        "--initial-delay",
        help="Initial delay in seconds before cleanup starts.",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--cleanup-interval",
        help="Delay in seconds between cleanup batches.",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--batch-size",
        help="Number of images to clean up per batch.",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--threshold-days",
        help="Age threshold in days for images to be cleaned up.",
        type=int,
        default=CLEANUP_THRESHOLD_DAYS,
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s]: %(message)s",
        filename=args.devkit_log_file,
        filemode="a" if args.devkit_log_file else "w",
    )

    cancel_event = Event()
    try:
        cleanup_images(
            cancel_event,
            args.config_path,
            args.search_path,
            initial_delay=args.initial_delay,
            interval=args.cleanup_interval,
            batch_size=args.batch_size,
            threshold_days=args.threshold_days,
        )
    except KeyboardInterrupt:
        logging.info("Cleanup interrupted by user.")
        cancel_event.set()


if __name__ == "__main__":  # pragma: no cover
    main()
