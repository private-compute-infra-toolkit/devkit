# Changelog

All notable changes to this project will be documented in this file. See [commit-and-tag-version](https://github.com/absolute-version/commit-and-tag-version) for commit guidelines.

## 3.1.1 (2026-04-09)


### Bug Fixes

* avoid docker groupd ID conflicts
* docker image pulling

## 3.1.0 (2026-04-09)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.36.0
* **deps:** upgrade git in tool-env to 2.53.0


### Features

* automatically grant xhost permission for X11 display


### Bug Fixes

* **docs:** update prerequisites
* propagate host file descriptor limits to docker container

## 3.0.0 (2026-04-02)


### ⚠ BREAKING CHANGES

* The Go toolchain is no longer available in the
build-environment images. Any scripts or builds relying on go
inside the container will fail unless they install it separately
through the devkit.json image configuration optios.


### Dependencies

* **deps:** Upgrade gemini-cli to 0.35.2


### Features

* use uv for python dependencies
* mount only ~/.devkit/logs in the container
* refactor devkit/coverage to run on host via uv
* run devkit tools on host
* run devkit/bep Python code from outside of docker containers
* separate python progress logs from standard output
* simplify bazelisk installation and remove go from build-env

## 2.15.0 (2026-03-26)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.35.0
* **deps:** Upgrade gemini-cli to 0.35.1


### Features

* implement container event handler background service

## 2.14.0 (2026-03-23)


### Dependencies

* **deps:** Update ruff to 0.15.7
* **deps:** Update VSCode to 1.110.1
* **deps:** Upgrade gemini-cli to 0.33.2
* **deps:** Upgrade gemini-cli to 0.34.0


### Features

* Add --local flag to build script
* Add --no-cache flag to build script
* add background docker image cleanup
* add get_all_docker_image_tags function and refactor build logic
* add get_image_prefix to build script
* add image name allowlist and regex filtering to docker cleanup
* add manual entry point and configurable params to docker cleanup
* enforce devkit/ prefix in docker image namespaces
* implement actual docker image removal in cleanup script
* implement docker image cleanup logic and batch processing
* integrate docker image tag listing in background cleanup
* log stdout and stderr from docker rmi in cleanup script
* Rewrite scripts/docker_run into Python
* Support docker images namespaces
* support multiple target images in build script


### Bug Fixes

* Adjust function signature types per Python style guide ([84098e7]( )), closes [/google.github.io/styleguide/pyguide.html#31912]( )
* Use proper images search path


### Documentation

* Do not use pages subdirectory

## 2.13.0 (2026-03-13)


### Dependencies

* **deps:** Autoupdate pre-commit hooks
* **deps:** Bump github actions versions
* **deps:** Bump version of mypy pre-commit hook to 1.19.1
* **deps:** Upgrade gemini-cli to 0.33.0
* **deps:** Upgrade gemini-cli to 0.33.1
* **deps:** Upgrade ripgrep to 15.1.0


### Features

* Install ripgrep using github debian package

## 2.12.0 (2026-03-05)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.29.3
* **deps:** Upgrade gemini-cli to 0.29.5
* **deps:** Upgrade gemini-cli to 0.29.7
* **deps:** Upgrade gemini-cli to 0.30.0
* **deps:** Upgrade gemini-cli to 0.31.0
* **deps:** Upgrade gemini-cli to 0.32.1


### Features

* **devkit:** add vim to development environment
* Enable terminal with colors by default

## 2.11.0 (2026-02-19)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.29.2

## 2.10.0 (2026-02-12)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.27.3
* **deps:** Upgrade gemini-cli to 0.28.2

## 2.9.0 (2026-02-05)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.27.0


### Features

* Handle symlinks in project root
* Improve status message from checksum check

## 2.8.0 (2026-01-29)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.25.1
* **deps:** Upgrade gemini-cli to 0.25.2
* **deps:** Upgrade gemini-cli to 0.26.0


### Features

* Drop .bazelignore creation from docs


### Documentation

* devkit.json configuration

## 2.7.0 (2026-01-22)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.25.0


### Features

* Add alias for GCloud CLI
* Add AWS CLI
* Add custom keys and repositories support

## 2.6.0 (2026-01-15)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.24.0


### Features

* Add --native option to devkit/gemini
* Deprecate old script for finding root of project
* Rewrite script for finding root of the project

## 2.5.0 (2026-01-08)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.23.0


### Features

* Add check-toml to pre-commit hooks

## 2.4.0 (2025-12-29)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.21.1
* **deps:** Upgrade gemini-cli to 0.22.1


### Features

* Add devkit/vendor to support offline builds
* Add nitro-cli image
* Add pre-commit test for devkit/vendor


### Bug Fixes

* Switch to symbolic notation for `chmod`

## 2.3.0 (2025-12-11)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.19.3
* **deps:** Upgrade gemini-cli to 0.19.4
* **deps:** Upgrade gemini-cli to 0.20.0
* **deps:** Upgrade node.js to 22.21.1


### Features

* Check coverage thresholds in the C++ template
* Move devkit/test to ci/tests in template/cpp
* Run devkit/bep in the lightweight C++ template
* Run devkit/coverage in the supported C++ template

## 2.2.0 (2025-12-05)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.19.1


### Bug Fixes

* Run BEP generation from dev-env
* Safely handle GID conflicts during primary group creation

## 2.1.0 (2025-12-04)


### GitHub

* **github:** Symlinks now open jobs instead of images
* **github:** Upload logs in the case of failures


### Features

* Always check for tests status in templates


### Bug Fixes

* Run coverage tool in dev-env

## 2.0.0 (2025-12-03)


### ⚠ BREAKING CHANGES

* Simplify definition of custom packages
* Images customization and cleanup

### Dependencies

* **deps:** Upgrade gemini-cli to 0.15.0
* **deps:** Upgrade gemini-cli to 0.16.0
* **deps:** Upgrade gemini-cli to 0.17.1
* **deps:** Upgrade gemini-cli to 0.18.4


### GitHub

* **github:** Standardize GitHub Actions file extensions to .yaml


### Features

* Add --ipc=host to docker run
* Add --output-dir to devkit/bootstrap
* Add Google Chrome do ide-env
* Add option to specify extra PATH
* Add recommended extensions for C++ template
* Add schema validation for devkit.json
* Allow extra packages in docker images
* Always run devkit/bootstrap in DevKit original image
* Drop google-chrome version pinning
* Drop packages that can be now installed in clients
* Drop Python from client environment
* Images customization and cleanup
* Make config explicit/required in images build
* Mount DBUS_SESSION_BUS_ADDRESS
* Run `gcloud_setup` locally if dependencies are available
* Simplify definition of custom packages
* Specify versions for gh and jq tools
* Test custimization by adding tree package


### Bug Fixes

* Print docker check errors to stderr
* Simplify nvm installation commands

## 1.17.0 (2025-11-14)


### GitHub

* **github:** Add scorecards for github actions


### Features

* Handle GIT_DISCOVERY_ACROSS_FILESYSTEM

## 1.16.0 (2025-11-13)


### Dependencies

* **deps:** Update Gemini CLI to version 0.14.0


### GitHub

* **github:** Fix github workflows

## 1.15.0 (2025-11-12)


### Features

* Keep original path when mount is a symlink


### Bug Fixes

* Add comment explaning xtrace prompt
* **deps:** Pin buildifier to 6.1.1
* Improve clarity of debug vs non-debug mode

## 1.14.0 (2025-11-06)


### Dependencies

* **deps:** Update Gemini CLI to version 0.12.0


### Features

* Mount system bus socket by default


### Documentation

* Update Bazelisk link

## 1.13.0 (2025-11-04)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.11.3


### Features

* **docs:** Improve README.md
* Remove gcloud related code from build_and_run


### Bug Fixes

* Check if docker and docker buildx are installed
* Fix typo in example devkit/build command

## 1.12.0 (2025-10-29)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.10.0


### Features

* Add GitHub workflow for DevKit build and test


### Bug Fixes

* Do not push/pull docker images if docker registry is not defined
* Pass `GOOGLE_CLOUD_PROJECT` env variable to container
* **readme:** Fix readme setup numbered list
* Use bootstrap as the name of the program in usage text
* Use devkit's script name in its usage text


### Documentation

* Refine content of markdown docs and add usage examples

## 1.11.0 (2025-10-17)


### Dependencies

* **deps:** Include libxml2 in build-env-debian image
* **deps:** Upgrade gemini-cli to 0.9.0


### Bug Fixes

* Add template bootstrapping tests to tools/ci/pre-commit
* Ensure build.py handles empty string values in registry
* Remove template bootstrapping tests from tools/ci/pre-commit
* Set default value for SUFFIX
* Support comment lines in templates.txt

## 1.10.0 (2025-10-16)


### GitHub

* **github:** Adding gh actions for tools/ci


### Bug Fixes

* Avoid reuse of kokoro shell namespace
* Execute gitlint in debug mode

## 1.9.0 (2025-10-10)


### Dependencies

* **deps:** Upgrade gemini-cli to 0.8.2

## 1.8.0 (2025-10-10)


### Features

* Drop build-alpine image

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
