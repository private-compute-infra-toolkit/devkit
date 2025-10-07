# test

The `test` script is a validation tool for DevKit templates that is executed after a project is
bootstrapped. It validates build reproducibility and test execution by running a series of checks in
two separate environments.

First, it builds the DevKit build environment and runs the validation checks from within that
container. The checks include building the project, verifying file integrity, and running tests.

Second, it runs the same set of validation checks on the host system. This ensures that the
bootstrapped project is buildable and functional both within the DevKit containers and with a native
Bazel installation.

## Usage

```
{% include 'help/test.txt' %}
```
