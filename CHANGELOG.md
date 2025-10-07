# Changelog

All notable changes to this project will be documented in this file. See [commit-and-tag-version](https://github.com/absolute-version/commit-and-tag-version) for commit guidelines.

## 1.7.0 (2025-10-07)


### Dependencies

* **deps:** Update gemini-cli to 0.7.0

## 1.6.0 (2025-10-07)


### Features

* Refactor tests for build.py

### Documentation

* Documentation updates

## 1.5.0 (2025-10-02)


### Features

* Add ephemeral mode to VSCode IDE
* Do not use build-env for gcloud setup

## 1.4.0 (2025-09-26)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.6.1
* **deps:** Upgrade pre-commit hooks


### Features

* Reduce number of docker mounts
* Unify handling for external mounts

## 1.3.0 (2025-09-25)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.6.0


### Features

* Add --templates-root option to devkit/bootstrap
* Add gcloud setup scripts
* Add scorecard label to readme


### Bug Fixes

* Correct git submodule url
* Move docs generation to tools/ci/utils/build_docs


### Documentation

* Simplify bootstrap text

## 1.2.0 (2025-09-23)


### GitHub

* **github:** Adding dependabot yaml config
* **github:** Adds scorecard github action

## 1.1.0 (2025-09-19)


### Dependencies

* **deps:** Update Gemini CLI to 0.5.0-preview.1
* **deps:** Update Gemini CLI to 0.5.4
* **deps:** Update used Bazel to 8.4.1


### GitHub

* **github:** Add GitHub section to version config and changelog


### Features

* Add coverage test command
* Add DEVKIT_DOCKER_RUN_ARGS env var support
* Add get-architecture tool
* Add missing branch coverage info
* Add progress prints in docker build
* Add support for zip/unzip in the build-env
* Add variable expansion to docker run args
* added jinja2 template for bep tool
* added jinja2 template for bootstrap tool
* added jinja2 template for build tool
* added jinja2 template for checksums tool
* added jinja2 template for dev tool
* added jinja2 template for test tool
* added jinja2 template for vscode_ide tool
* Allow devkit/* execution from subdirectories
* Forward standrd input to devkit commands
* Include status into the progress of docker build
* Replace prints by logs in docker build
* Simplify and test the get-architecture tool
* Standardize and control get-architecture output


### Bug Fixes

* Capture only stdout in build_docs
* Docker run args from devkit.json
* Find external mounts from project root
* Invert logic in coverage check

## 1.0.0 (2025-09-11)


### ⚠ BREAKING CHANGES

* Delete devkit/.bazelrc

### Features

* Add GoLand IDE support
* Added bep.txt file in doc/help
* Added bootstrap.txt file in docs/help
* Added check_checksums.txt file in doc/help
* Added dev.txt file in doc/help
* Added test.txt file in doc/help
* Added vscode_ide.txt file in doc/help
* Delete devkit/.bazelrc
* fixed bep.txt file in doc/help
* Hide docker/build.py script from the user
* Ignore .venv directories during scan
* Switch to CFC sysroot


### Bug Fixes

* Improve symlink resolution
* Improve symlink resolution (part 2/2)
* Print usage to stdout

## 0.6.0 (2025-09-05)


### Features

* Automatic mounting of .git dir
* ignore bazel-* symlinks recursively


### Bug Fixes

* Proper handling of relative symlinks

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
