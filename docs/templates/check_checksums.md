# check_checksums

The `check_checksums` tool is used to verify build reproducibility.

After a project is bootstrapped, it will contain a `checksums.txt` file with an expected checksum
for the build artifact. This script automates the process of checking the artifact's checksum
against the expected value and shows any discrepancies in an easy-to-read format.

## Usage

```
{% include 'help/check_checksums.txt' %}
```

## Example

```sh
devkit/check_checksums
```
