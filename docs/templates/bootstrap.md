# bootstrap

The `bootstrap` script is used to create new projects from a set of predefined templates. It's the
perfect starting point for a new service, library, or other component, as it ensures that all the
necessary boilerplate and configuration are set up correctly from the beginning.

This tool uses the Jinja2 templating engine, processing a directory tree of template files. You can
pass in a context of key-value pairs as arguments, allowing for flexible and dynamic project
generation.

The entire process runs within the `tool-env` container, guaranteeing a consistent and reliable
bootstrapping experience regardless of your local machine's setup.

## Usage

```
{% include 'help/bootstrap.txt' %}
```

## Example

```sh
devkit/bootstrap --template cpp --args toolchain=llvm_bootstrapped
```
