# devkit.json Configuration

The `devkit.json` file is the central configuration file for the DevKit. It allows you to customize
various aspects of the toolkit, primarily focusing on Docker image management and dependency
versions.

## Configuration Parameters

| Path                                      | Type   | Description                                                                                                                                    |
| :---------------------------------------- | :----- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| `docker`                                  | Object | Top-level configuration section for Docker settings.                                                                                           |
| `docker.registry`                         | Object | Configuration for the container registry where images are stored.                                                                              |
| `docker.registry.host`                    | String | The hostname of the container registry (e.g., `us-docker.pkg.dev`).                                                                            |
| `docker.registry.project`                 | String | The project ID within the registry (e.g., `my-project`).                                                                                       |
| `docker.registry.repository`              | String | The repository name within the project (e.g., `my-repo`).                                                                                      |
| `docker.run`                              | List   | A list of additional commands or arguments (usage depends on context).                                                                         |
| `docker.images`                           | Map    | A dictionary where keys are image names (e.g., `build-env`, `build-env-debian`) and values are their specific configurations.                  |
| `docker.images.<image_name>`              | Object | Configuration for a specific Docker image.                                                                                                     |
| `docker.images.<image_name>.keys`         | Map    | A map of GPG keys to add. Keys are identifiers, values are URLs to the public key. Passed as `EXTRA_KEYS` build arg.                           |
| `docker.images.<image_name>.repositories` | Map    | A map of package repositories to add. Keys are identifiers, values are repository URLs. Passed as `EXTRA_REPOSITORIES` build arg.              |
| `docker.images.<image_name>.packages`     | Map    | A map of extra packages to install. Keys are package names, values are version strings (e.g., `1.11.*`). Passed as `EXTRA_PACKAGES` build arg. |

## Example

```json
{
    "docker": {
        "registry": {
            "host": "us-docker.pkg.dev",
            "project": "my-project",
            "repository": "my-repo"
        },
        "images": {
            "build-env": {
                "keys": {
                    "hashicorp": "https://apt.releases.hashicorp.com/gpg"
                },
                "repositories": {
                    "hashicorp": "https://apt.releases.hashicorp.com"
                },
                "packages": {
                    "terraform": "1.11.*"
                }
            }
        }
    }
}
```
