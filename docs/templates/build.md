# build

The `build` script is your main gateway into the containerized build environment. Its primary
purpose is to provide a consistent, reproducible, and hermetic environment for all build and
test-related tasks. By running builds inside a container, you eliminate the "works on my machine"
problem.

This environment is packed with all the essential tools required for a robust build process,
including Bazel, the Google Cloud SDK (`gcloud`), `buildifier` for BUILD file formatting, `jq` for
JSON manipulation, and many others.

You can use the script in two main ways: 1. **Execute a command:** Pass any command and its
arguments to the script, and it will be executed inside the container. For example:
`build bazel build //...` 2. **Interactive session:** If you run the script with no arguments, it
will drop you into an interactive `bash` shell inside the container, allowing you to explore the
environment and run commands manually.

## Usage

```
{% include 'help/build.txt' %}
```
