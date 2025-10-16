# DevKit

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/private-compute-infra-toolkit/devkit/badge)](https://scorecard.dev/viewer/?uri=github.com/private-compute-infra-toolkit/devkit)

_Faster, Safer, Easier TEE Development._

DevKit is a tooling package built to accelerate development, improve code quality, and ensure
consistency across Private Compute Infrastructure Toolkit projects utilizing
[Trusted Execution Environments (TEE)](https://en.wikipedia.org/wiki/Trusted_execution_environment).
faster, safer, and easier.

## Required

-   Sudo-less [Docker](https://www.docker.com/)
-   [Docker Buildx plugin](https://github.com/docker/buildx)
-   [Python 3](https://www.python.org/downloads/) installed on your Linux machine.
-   [Bazelisk](https://github.com/bazelbuild/bazelisk/releases/download/) to be able to build code
    outside of DevKit containers

## Setup

1. Add DevKit as a submodule to your new or existing git repository. Replace `release-<version>`
   with the version you require from the available
   [branch releases](https://github.com/private-compute-infra-toolkit/devkit/branches/all?query=release-).

```sh
git submodule add --name=devkit --branch=release-<version> https://github.com/private-compute-infra-toolkit/devkit.git .devkit
```

1. Add a linux symlink to the DevKit entrypoint scripts.

```sh
ln -s .devkit/devkit devkit
echo ".devkit" >> .bazelignore
```

1. Bootstrap the project.

> [!CAUTION] Take care to back up your files if you have executed the bootstrap command before.
> Files that have been generated from previous bootstraps will be overwritten.

For the full list of supported templates and toolchains, navigate
[here](https://github.com/private-compute-infra-toolkit/devkit/blob/main/templates.txt).

```sh
devkit/bootstrap --template cpp --args toolchain=llvm_custom_sysroot
```

1. Build and spin up containerized build environment to start developing. To start other variants,
   use the corresponding `devkit/build-<variant>` script. Supported variants include `debian` and
   `rockylinux`.

```sh
devkit/build bazel build //...
```

Begin development by spinning up a container-based local development environment from the root of
your project.

```sh
devkit/dev
devkit/vscode_ide --server # Spins up VS Code IDE in a local server at localhost:8080
```
