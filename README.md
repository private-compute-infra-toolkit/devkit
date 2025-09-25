# DevKit

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/private-compute-infra-toolkit/devkit/badge)](https://scorecard.dev/viewer/?uri=github.com/private-compute-infra-toolkit/devkit)

## Bootstrapping a new project

To start a new project using a DevKit template, follow these steps:

1.  Create a directory for your new project and navigate into it:

    ```bash
    mkdir my-new-project
    cd my-new-project
    ```

2.  Add DevKit to your project:

    You may test DevKit locally by:

    ```bash
    ln -s /your/path/to/devkit/devkit devkit
    ```

    For proper setup, add DevKit as a submodule:

    ```bash
    git submodule add --name=devkit --branch=main https://github.com/private-compute-infra-toolkit/devkit.git .devkit
    ln -s .devkit/devkit devkit
    printf "\n.devkit\n" >>.bazelignore
    ```

3.  Run the bootstrap script with your desired template:

    ```bash
    devkit/bootstrap --template <template> --args [key=value ...]
    ```

    Example:

    ```bash
    devkit/bootstrap --template cpp --args toolchain=llvm_bootstrapped
    ```

    Full list of supported templates and parameters can be found in the `templates.txt` file.

This populates your current directory with the files from the chosen template, ready for you to
start developing.

## Running build images

To start the default image:

```bash
devkit/build
```

To start other variants, use the corresponding `devkit/build-<variant>` script. Supported variants
include `alpine`, `debian` and `rockylinux`.

```bash
devkit/build-debian
```
