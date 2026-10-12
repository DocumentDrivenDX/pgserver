# PostgreSQL wheels for pgserver

DocumentDrivenDX fork of [orm011/pgserver](https://github.com/orm011/pgserver),
for applications and tests that need a self-contained PostgreSQL server.
PostgreSQL 18 can match the major version used by Lakebase; this does not claim
full Lakebase feature parity.

## Versions and platforms

The minor release pins below are maintained from the official
[PostgreSQL version table](https://www.postgresql.org/support/versioning/), are:

| PostgreSQL | Python distribution | Distribution version | pgvector |
| --- | --- | --- | --- |
| 16.15 | `pgserver-pg16` | `16.15.1` | 0.8.6 |
| 17.11 | `pgserver-pg17` | `17.11.1` | 0.8.6 |
| 18.6 | `pgserver-pg18` | `18.6.1` | 0.8.6 |

Each version builds on native **Linux x86_64**, **Linux aarch64**, and
**macOS arm64** runners. Linux wheels target manylinux; macOS has a macOS 14
minimum. The matrix builds and tests CPython 3.10–3.13 wheels. Successful
workflow artifacts and release assets establish availability for each target.
Intel macOS and Windows are outside the current build matrix.

All three distributions retain the Python import `pgserver`. Install only
one in an environment: they own the same imports, as does upstream `pgserver`.
Ordinary wheel installation does not compile PostgreSQL.

## Install

Select a wheel matching your PostgreSQL major, Python version, and platform
from [Releases](https://github.com/DocumentDrivenDX/pgserver/releases):

```sh
uv pip install /path/to/pgserver_pg17-17.11.1-<python-and-platform-tags>.whl
# A full GitHub Release asset URL works in place of the local path.
```

No PyPI publication. Release tags are recorded in `build-versions.json`.
They normally use `pg<version>-pgv<version>`; a revision suffix distinguishes
changes to packaging for the same native versions. The expanded PG18 platform
set uses `pg18.6-pgv0.8.6-r2` to preserve the initial tag's history.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import pgserver

with TemporaryDirectory(prefix="pg-test-") as root:
    with pgserver.get_server(Path(root) / "data") as server:
        print(server.get_uri())
```

On Unix the upstream API disables TCP and selects a Unix socket directory.
Use a separate data directory per test worker and keep one server alive per
worker. See [upstream usage](UPSTREAM-README.md).

## Build and update

The source of truth is `build-versions.json`: versions, trusted source SHA256
checksums, distribution identities, and release tags. To build a selected major
in a clean checkout:

```sh
python3 scripts/select-postgres.py 17
make
python -m build --wheel
```

`make` builds the native binaries once and repairs loader paths so installation
can relocate them. Native prerequisites include a C compiler, make, Python 3,
curl, bison, flex, zlib development headers, and patchelf on Linux. Source
installs require `make` first. A selected major requires a clean native install
to prevent reuse of binaries from a different PostgreSQL version.

### Automatic minor release updates

The `Automatically update PostgreSQL minor releases` GitHub workflow runs every
six hours (00:23, 06:23, 12:23, 18:23 UTC), and can be dispatched manually.
GitHub may delay scheduled runs. It reads the official
[stable-version feed](https://www.postgresql.org/versions.rss), tracks only
PostgreSQL 16, 17, and 18, rejects downgrades and prereleases, and downloads each
new source archive to verify the official SHA256 before committing new pins.
The checksum, distribution version, release tag, README table, and PG18 default
build metadata are updated together. pgvector remains separately pinned.

A missing or draft release triggers the same nine-job build/test matrix used
for manual publication. All nine must pass before a new release is published.
Every release must contain all twelve Python/platform wheels and checksums;
provenance attestations are generated before upload. Uploads use drafts and
can be retried on the next scheduled check. Existing complete public releases
are skipped and never overwritten. Network, validation and test failures fail
the workflow and leave publication gated. GitHub Actions provides failure
notifications according to repository/account subscription settings.

Checks with no new version or incomplete release skip native builds. A monthly
verification receipt commit keeps the public scheduled workflow active between
quarterly PostgreSQL releases, avoiding GitHub's 60-day inactivity disablement.
No personal access token, external scheduler, or Codex follow-up is required;
the workflow uses the repository's scoped `GITHUB_TOKEN`.

For an intentional manual packaging or pgvector update, change
`build-versions.json`, keep default PG18 metadata aligned, choose new release
tags, then dispatch `Build verified release wheels` from `main` with
`publish=true`. Existing published assets remain immutable.

PostgreSQL minor releases normally arrive roughly quarterly; consult its
[release schedule](https://www.postgresql.org/developer/roadmap/).

## Licenses and changes

The Python wrapper retains upstream Apache-2.0 [LICENSE](LICENSE), attribution,
and history. [NOTICE](NOTICE) identifies fork changes. PostgreSQL and pgvector
use the PostgreSQL license; their source license texts are included in wheels.
The fork keeps the caller API and changes build versions, checksum validation,
portable pgvector flags, relocatable native libraries, license packaging,
and release automation.
