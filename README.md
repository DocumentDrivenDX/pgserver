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
| 16.16 | `pgserver-pg16` | `16.16.0` | 0.8.6 |
| 17.12 | `pgserver-pg17` | `17.12.0` | 0.8.6 |
| 18.7 | `pgserver-pg18` | `18.7.0` | 0.8.6 |

Wheels are built for **Linux x86_64**, **Linux aarch64** (manylinux_2_17) and
**macOS arm64** (macOS 14+), CPython 3.11-3.14. Intel macOS and Windows are not
built. The product tests run in CI on Linux for each major; macOS wheels are
built and tested by the release workflow only.

All three distributions provide the Python import `pgserver`, as does upstream
[`pgserver`](https://pypi.org/project/pgserver/) from orm011. **Install only
one of them in an environment**: they own the same import and will overwrite
each other's files. Ordinary wheel installation does not compile PostgreSQL.

## Install

From the next release, from PyPI (pick one major):

```sh
pip install pgserver-pg18   # or pgserver-pg17 / pgserver-pg16
```

Until then, install the current wheels from the GitHub Releases:

```sh
pip install pgserver-pg18 \
  --find-links https://github.com/DocumentDrivenDX/pgserver/releases/expanded_assets/pg18.6-pgv0.8.6-r2
# pg17: .../expanded_assets/pg17.11-pgv0.8.6-r1   pg16: .../expanded_assets/pg16.15-pgv0.8.6-r1
```

Each release also lists `SHA256SUMS`. A wheel can be installed directly from its
asset URL too. Release tags for the existing wheels are recorded in
`build-versions.json`.

## Quickstart

<!-- quickstart -->
```python
from pathlib import Path
from tempfile import TemporaryDirectory
import pgserver

with TemporaryDirectory(prefix="pg-") as root:
    with pgserver.get_server(Path(root) / "data") as server:
        print(server.psql("select version();"))
        print(server.psql("create extension if not exists vector; "
                          "select extversion from pg_extension where extname='vector';"))
```
<!-- /quickstart -->

On Unix the upstream API disables TCP and selects a Unix socket directory.
Use a separate data directory per test worker and keep one server alive per
worker. See [upstream usage](UPSTREAM-README.md). CI executes this quickstart
against every built wheel.

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

### Releasing

The `release` workflow runs only on a tag named `pgserver-pgNN-vX.Y.Z` (the
version must equal `package_version` in `build-versions.json`). It builds the
twelve wheels for that major, runs the product tests and the README quickstart,
smoke-tests the built wheel in a fresh venv, publishes to PyPI with trusted
publishing and creates a GitHub Release with the wheels and `SHA256SUMS`. A manual
dispatch runs the build and smoke tests only (`dry_run` defaults to true).

### Automatic minor release updates

The `Automatically update PostgreSQL minor releases` workflow runs every six
hours and can be dispatched manually. It reads the official
[stable-version feed](https://www.postgresql.org/versions.rss), tracks only
PostgreSQL 16, 17 and 18, rejects downgrades and prereleases, and verifies each
new source archive against the official SHA256 before committing new pins.
The checksum, distribution version, README table and PG18 default build
metadata are updated together; pgvector remains separately pinned. The run
summary lists majors whose pinned version is not on PyPI yet
(`python scripts/update-postgres.py --pending`); tag a release to publish them.
A monthly state commit keeps the scheduled workflow from being disabled after
60 days of inactivity.

PostgreSQL minor releases normally arrive roughly quarterly; consult its
[release schedule](https://www.postgresql.org/developer/roadmap/).

## Licenses and changes

The Python wrapper retains upstream Apache-2.0 [LICENSE](LICENSE), attribution,
and history. [NOTICE](NOTICE) identifies fork changes. PostgreSQL and pgvector
use the PostgreSQL license; their source license texts are included in wheels.
The fork keeps the caller API and changes build versions, checksum validation,
portable pgvector flags, relocatable native libraries, license packaging,
and release automation.

See [CHANGELOG.md](CHANGELOG.md).
