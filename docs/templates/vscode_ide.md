# vscode_ide

The `vscode_ide` script launches a fully containerized Visual Studio Code development environment.
This provides a consistent and reproducible IDE setup, complete with all necessary tools and
extensions, regardless of your local machine's configuration.

The script ensures that your settings, extensions, and other VS Code configurations are persisted
across sessions by mounting configuration directories from your home directory (like
`~/.config/Code` and `~/.vscode`) into the container.

It supports two modes of operation:

1.  **Desktop Mode (default):** This launches a graphical VS Code window on your local desktop by
    integrating with your system's X11 server. It's ideal for a traditional desktop experience.
2.  **Server Mode (`--server`):** This runs VS Code as a web server inside the container, which you
    can access from your local web browser. This is perfect for remote development or running the
    IDE on a headless machine.

## Usage

```
{% include 'help/vscode_ide.txt' %}
```

## Example

```sh
devkit/vscode_ide --server
```
