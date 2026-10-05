# check_checksums

<!-- [START check_checksums_overview] -->

The `check_checksums` tool is used to verify build reproducibility.

After a project is bootstrapped, it will contain a `checksums.txt` file with an
expected checksum for the build artifact. This script automates the process of
checking the artifact's checksum against the expected value and shows any
discrepancies in an easy-to-read format.

<!-- [END check_checksums_overview] -->

## Usage

<!-- [START check_checksums_usage] -->

```
{% include 'help/check_checksums.txt' %}
```

<!-- [END check_checksums_usage] -->

## Example

<!-- [START check_checksums_example] -->

```sh
devkit/check_checksums
```

<!-- [END check_checksums_example] -->
