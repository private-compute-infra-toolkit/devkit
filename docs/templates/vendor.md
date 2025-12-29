# vendor

The `vendor` tool facilitates offline builds by allowing you to "vendor" (export) Docker images into
a portable format and then load them back into the Docker environment.

This is particularly useful in air-gapped environments or scenarios where internet access is
restricted or unreliable. By pre-downloading and saving the required Docker images (like `tool-env`,
`build-env`) into an archive, you can transfer them to the offline machine and load them, ensuring
that the DevKit tools can function without needing to pull from a remote registry.

The tool leverages the `docker save` and `docker load` commands under the hood, streamlining the
process of managing these dependencies for offline usage.

## Usage

```
{% include 'help/vendor.txt' %}
```

## Example

Vendor specific images

```sh
devkit/vendor --dir /tmp/images tool-env build-env
```

Load images from a directory

```sh
devkit/vendor --dir /tmp/images --load
```
