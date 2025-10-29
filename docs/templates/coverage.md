# coverage

The `coverage` tool allows to generate and validate a coverage report for a Bazel workspace.

It allows you to fine-tune line and branch coverage threshold per file that must be reached for the
report to pass.

This tool is based on `bazel coverage` and because of that it supports multiple programming
languages (e.g.: Rust, C++ or Java).

## Usage

```
{% include 'help/coverage.txt' %}
```

## Example

```sh
devkit/coverage --lines 90 --branch 80
```
