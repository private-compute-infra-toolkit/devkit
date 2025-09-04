# Changelog

All notable changes to this project will be documented in this file. See [commit-and-tag-version](https://github.com/absolute-version/commit-and-tag-version) for commit guidelines.

## 0.5.0 (2025-09-04)


### Dependencies

* **deps:** Upgrade bazelisk to v1.27.0


### Features

* Add validation of devkit/build --help
* Implementation of -h/--help flags inside bootstrap script
* Implementation of -h/--help flags inside build script
* Implementation of help dialog for dev tool


### Bug Fixes

* Add missing run-hook for gitlint
* Add needed --privileged flag for X11 VSCode
* Add repository_cache option in BEP generating command

## 0.4.0 (2025-09-02)


### Dependencies

* **deps:** Update addlicense to 1.2.0
* **deps:** Update buildifier pre-commit hook to latest


### Features

* Add bep generation command
* Add mpm support
* Implementation of -h/--help flag in check_checksums script
* Move docker_run and entrypoint_docker
* Move Dockerfiles out of the devkit directory
* Move test_entrypoint
* Remove code copied from build-system
* Simplify deps.json structure
* Simplify GitHub CLI setup
* Use commit-and-tag-version from DevKit


### Bug Fixes

* Align .gitlint with .versionrc.json
* Do not use symlink for .gitignore
* Exclude bazel-* symlinks from searching
* Exit immediately for unrecognized arg

## 0.3.0 (2025-08-27)


### Features

* Add gitlint pre-commit hook
* Implementation of -h/--help flags inside of test_entrypoint script
* Implementation of flag reading in get-architecture tool


### Bug Fixes

* Add gitlint fix for release commits
* Correct misspelling in variable name

## 0.2.0 (2025-08-26)


### Features

* Add fdfind and ripgrep to dev-env image
* Add jq wrapper script
* Add mount for $HOME/.devkit
* Add option to specify docker run args
* Add support for devkit.json config file
* Add support for gitlint
* Adding Neovim script
* Collect debug logs by default
* Gemini with MCP servers from Google3
* LOAS auth for Gemini with MCP servers
* Propagate CLI flags to the underlying binary
* Rewrite script for listing external mounts
* Support for code checkout with RPC link
* Support gcert and uplink-helper


### Bug Fixes

* Add check to ensure script is sourced
* Add missing required files for open source
* Disable C++ toolchain lookup
* Rename --devkit-json-path to --config
* Rename logging -> lib_logging.sh
* Stop depending on jq

## 0.1.0 (2025-08-13)


### Features

* Initial release
