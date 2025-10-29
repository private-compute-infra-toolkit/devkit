# dev

The `dev` script is your entry point into the DevKit development environment.

This environment is separate from the `build` environment. While the `build` environment focuses on
building and testing, the `dev` environment is tailored for your day-to-day development workflow. It
comes equipped with an extra set of tools for development tasks, such as code quality checkers,
commit hooks, and AI-assisted development tools. These include `pre-commit` for running checks
before you commit, `gitlint` for enforcing commit message conventions, and `gemini` for interacting
with Google's AI models.

Similar to the `build` script, you can execute a command directly (e.g., `dev gemini`) or launch an
interactive `bash` session to work inside the container.

## Usage

```
{% include 'help/dev.txt' %}
```

## Example

```sh
devkit/dev gemini
```
