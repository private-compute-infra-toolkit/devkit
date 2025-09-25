# dev

The `dev` script is your entry point to a containerized development environment, which is separate
from the `build` environment. While the `build` environment is focused on hermetic builds and
testing, the `dev` environment is designed to support your day-to-day development workflow.

It comes equipped with a different set of tools tailored for development tasks, such as code quality
checkers, commit hooks, and AI-assisted development tools. This includes `pre-commit` for running
checks before you commit, `gitlint` for enforcing commit message conventions, and `gemini` for
interacting with Google's AI models.

Just like the `build` script, you can execute a command directly (e.g.,
`dev pre-commit run --all-files`) or launch an interactive `bash` session to work within the
container.

## Usage

```
{% include 'help/dev.txt' %}
```
