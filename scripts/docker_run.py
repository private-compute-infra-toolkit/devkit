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
This script runs a docker container with the necessary mounts and environment.
"""

import argparse
import grp
import json
import logging
import os
import pwd
import shlex
import signal
import socket
import subprocess
import sys
from pathlib import Path
from collections.abc import MutableSequence, Sequence
from find_project_root import find_project_root
from list_external_mounts import get_minimal_mounts
from docker_cleanup import start_background_cleanup


def path_from_env(env_var: str, default: Path) -> Path:
    """Returns a Path from an environment variable, or a default value."""
    val = os.environ.get(env_var)
    return Path(val) if val else default


def main() -> None:
    """
    Parses arguments, configures the environment, and executes the docker container.

    This function identifies the project root, determines host and container
    paths (including home and temporary directories), and prepares a minimal
    set of volume mounts. it also handles user/group mapping, environment
    variable propagation, and incorporates additional docker run arguments
    from 'devkit.json' or environment variables before executing the container.
    """
    scripts_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run a docker container with the necessary mounts and environment.",
        add_help=False,
    )
    parser.add_argument(
        "--devkit-log-file",
        help="Path to a file for logging. If not specified, logs to stderr.",
        type=Path,
    )
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s]: %(message)s",
        filename=args.devkit_log_file,
        filemode="a" if args.devkit_log_file else "w",
    )

    try:
        host_project_root = path_from_env(
            "DEVKIT_HOST_PROJECT_ROOT", find_project_root()
        )
        logging.info("Host project root: %s", host_project_root)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    container_project_root = path_from_env(
        "DEVKIT_CONTAINER_PROJECT_ROOT", host_project_root
    )

    command_project_root = path_from_env(
        "DEVKIT_COMMAND_PROJECT_ROOT", host_project_root
    )

    logging.info("Container project root: %s", container_project_root)
    logging.info("Command project root: %s", command_project_root)

    host_home = path_from_env("DEVKIT_HOST_HOME", Path.home())
    command_home = path_from_env("DEVKIT_COMMAND_HOME", host_home)
    container_home = path_from_env("DEVKIT_CONTAINER_HOME", host_home)

    tmpdir = Path(os.environ.get("TMPDIR", "/tmp"))
    host_tmp_dir = path_from_env("DEVKIT_HOST_TMP_DIR", tmpdir)
    container_tmp_dir = path_from_env("DEVKIT_CONTAINER_TMP_DIR", host_tmp_dir)

    home_files: Sequence[Path] = [Path(".gitconfig")]
    home_dirs: Sequence[Path] = [
        Path(".cache/bazel"),
        Path(".cache/bazelisk"),
        Path(".cache/buf"),
        Path(".cache/go-build"),
        Path(".cache/nvim"),
        Path(".cache/pip"),
        Path(".cache/pip-tools"),
        Path(".cache/pre-commit"),
        Path(".cache/pylint"),
        Path(".config/gcloud"),
        Path(".config/google-chrome"),
        Path(".config/matplotlib"),
        Path(".devkit"),
        Path(".docker"),
        Path(".gemini"),
        Path(".local/pre-commit"),
        Path(".local/share/nvim"),
        Path(".local/state"),
        Path(".npm"),
        Path(".vim"),
    ]

    docker_sock = Path("/var/run/docker.sock")
    system_bus_socket = Path("/run/dbus/system_bus_socket")

    mounts: MutableSequence[Path] = [
        docker_sock,
        system_bus_socket,
    ]

    user_name = os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name
    user_id = int(os.environ.get("USER_ID") or os.getuid())
    group_name = os.environ.get("GROUP") or grp.getgrgid(os.getgid()).gr_name
    group_id = int(os.environ.get("GROUP_ID") or os.getgid())

    session_bus_socket = Path("/run/user") / str(user_id) / "bus"
    mounts.append(session_bus_socket)

    for rel_path in home_dirs:
        dir_path = command_home / rel_path
        dir_path.mkdir(parents=True, exist_ok=True)
        mounts.append(dir_path)

    for rel_path in home_files:
        file_path = command_home / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch(exist_ok=True)
        mounts.append(file_path)

    additional_env: MutableSequence[str] = []
    additional_paths: MutableSequence[Path] = []

    try:
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if git_check.returncode == 0 and git_check.stdout.strip() == "true":
            git_dir = Path(
                subprocess.check_output(
                    ["git", "rev-parse", "--absolute-git-dir"], text=True
                ).strip()
            )
            if not git_dir.is_relative_to(Path.cwd()):
                logging.info("Adding out-of-tree git directory to mounts: %s", git_dir)
                mounts.append(git_dir)
                additional_env.append("--env=GIT_DISCOVERY_ACROSS_FILESYSTEM=1")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.info("Git discovery failed or not in a git repo: %s", e)

    docker_group = "docker"
    try:
        docker_group_id = grp.getgrnam(docker_group).gr_gid
    except KeyError:
        docker_group_id = 0
        logging.info("Group %s not found, defaulting GID to 0", docker_group)

    nobody_group = "nobody"
    try:
        nobody_group_id = grp.getgrnam(nobody_group).gr_gid
    except KeyError:
        nobody_group_id = 0
        logging.info("Group %s not found, defaulting GID to 0", nobody_group)

    if nobody_group_id > 0:
        additional_env.append(f"--env=NOBODY_GROUP_ID={nobody_group_id}")

    minimal_mounts: set[Path] = get_minimal_mounts(command_project_root, mounts)
    logging.info(
        "Resolved %d minimal mounts out of %d requested",
        len(minimal_mounts),
        len(mounts),
    )

    docker_run_args: MutableSequence[str] = []
    if sys.stdin.isatty() and sys.stdout.isatty():
        docker_run_args.extend(["--interactive", "--tty"])
    elif not sys.stdin.isatty():
        docker_run_args.append("--interactive")

    devkit_json_path = command_project_root / "devkit.json"

    try:
        if devkit_json_path.exists():
            with open(devkit_json_path) as f:
                data = json.load(f)
                run_args = data.get("docker", {}).get("run", [])
                if run_args:
                    logging.info(
                        "Loaded docker run args from devkit.json: %s", run_args
                    )
                    docker_run_args.extend(run_args)
    except Exception as e:
        logging.warning("Failed to parse devkit.json: %s", e)

    if os.environ.get("DEVKIT_DOCKER_RUN_ARGS"):
        env_args = shlex.split(os.environ["DEVKIT_DOCKER_RUN_ARGS"])
        logging.info("Adding args from DEVKIT_DOCKER_RUN_ARGS: %s", env_args)
        docker_run_args.extend(env_args)

    evaluated_args = [os.path.expandvars(arg) for arg in docker_run_args]

    docker_mounts: MutableSequence[str] = []
    for path in minimal_mounts:
        host_path = path
        container_path = path
        if path.is_relative_to(command_home):
            suffix = path.relative_to(command_home)
            host_path = host_home / suffix
            container_path = container_home / suffix
        docker_mounts.append(f"--volume={host_path}:{container_path}")

    additional_path_val = ":".join(str(p) for p in additional_paths)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        f"--volume={host_project_root}:{container_project_root}",
        f"--workdir={Path.cwd()}",
        f"--env=HOME={container_home}",
        "--env=GOOGLE_CLOUD_PROJECT",
        "--env=GEMINI_API_KEY",
        "--env=AWS_SECRET_ACCESS_KEY",
        "--env=AWS_ACCESS_KEY_ID",
        "--env=AWS_SESSION_TOKEN",
        "--env=GH_TOKEN",
        f"--env=USER={user_name}",
        f"--env=USER_ID={user_id}",
        f"--env=GROUP={group_name}",
        f"--env=GROUP_ID={group_id}",
        f"--env=TMPDIR={container_tmp_dir}",
        "--env=TERM=xterm-256color",
        "--env=COLORTERM",
        f"--env=DOCKER_GROUP={docker_group}",
        f"--env=DOCKER_GROUP_ID={docker_group_id}",
        f"--env=NOBODY_GROUP={nobody_group}",
        f"--env=DBUS_SYSTEM_BUS_ADDRESS=unix:path={system_bus_socket}",
        f"--env=DBUS_SESSION_BUS_ADDRESS=unix:path={session_bus_socket}",
        f"--env=ADDITIONAL_PATH={additional_path_val}",
    ]
    docker_cmd.extend(additional_env)
    docker_cmd.extend(docker_mounts)
    docker_cmd.extend(
        [
            "--net=host",
            "--ipc=host",
            f"--hostname={socket.gethostname()}",
            f"--volume={host_tmp_dir}:{container_tmp_dir}",
            f"--entrypoint={scripts_dir / 'entrypoint_docker'}",
        ]
    )
    docker_cmd.extend(evaluated_args)
    docker_cmd.extend(unknown_args)

    logging.info("%s", shlex.join(docker_cmd))

    thread, cancel_event = start_background_cleanup(
        devkit_json_path, [scripts_dir.parent / "images"]
    )

    try:
        result = subprocess.run(docker_cmd, check=False)
        return_code = result.returncode
    except KeyboardInterrupt:
        exit_code_sigint = 128 + signal.SIGINT
        return_code = exit_code_sigint
    finally:
        cancel_event.set()
        thread.join(timeout=1.0)

    sys.exit(return_code)


if __name__ == "__main__":  # pragma: no cover
    main()
