# check_checksums

The `check_checksums` script is a crucial utility for ensuring file integrity. It provides a simple
yet effective way to verify that files have not been altered or corrupted.

The script operates by reading a manifest file named `checksums.txt` located in the current
directory. This file should contain one entry per line, with each line consisting of a SHA-256
checksum, two spaces, and the corresponding filename. The script iterates through this manifest,
calculates the SHA-256 checksum of each file on disk, and compares it against the expected value
from the manifest.

This is particularly useful in CI/CD pipelines or after downloading artifacts to guarantee that you
are working with the correct and untampered versions of files. It is a standalone script and does
not run within a container.

## Usage

```
{% include 'help/check_checksums.txt' %}
```
