# bep

The `bep` tool is a powerful utility for analyzing Bazel builds. It generates detailed reports in
the Build Event Protocol (BEP) format, which provides a structured stream of events about a build's
execution. This data is invaluable for debugging build failures, analyzing dependency graphs, and
understanding build performance.

The tool operates by running the `bazel fetch` or `bazel build` command for specified targets within
the containerized `build-env`. The output is a collection of JSON files, one for each target, which
can be consumed by other analysis and visualization tools.

If no specific targets are provided, the tool will analyze all targets within the workspace
(`//...`).

## Usage

```
{% include 'help/bep.txt' %}
```

## Example

```sh
devkit/bep --target BUILD --command fetch --output_dir bep_report/
```
