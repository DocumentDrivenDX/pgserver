# PostgreSQL wheels for pgserver

DocumentDrivenDX fork of [orm011/pgserver](https://github.com/orm011/pgserver),
for applications and tests that need a self-contained PostgreSQL server.
PostgreSQL 18 can match the major version used by Lakebase; this does not claim
full Lakebase feature parity.

## Versions and platforms

The pinned latest minor releases, checked on 2026-10-11 against the official
[PostgreSQL version table](https://www.postgresql.org/support/versioning/), are:

| PostgreSQL | Python distribution | Distribution version | pgvector |
| --- | --- | --- | --- |
| 16.15 | `pgserver-pg16` | `16.15.0` | 0.8.6 |
| 17.11 | `pgserver-pg17` | `17.11.0` | 0.8.6 |
| 18.6 | `pgserver-pg18` | `18.6.0` | 0.8.6 |

Each version builds on native **Linux x86_64**, **Linux aarch64**, and
**macOS arm64** runners. Linux wheels target manylinux; macOS has a macOS 14
minimum. The matrix builds and tests CPython 3.9–3.13 wheels. Successful
workflow artifacts and release assets establish availability for each target.
Intel macOS and Windows are outside the current build matrix.

All three distributions retain the Python import `pgserver`. Install only
one in an environment: they own the same imports, as does upstream `pgserver`.
Ordinary wheel installation does not compile PostgreSQL.

## Install

Select a wheel matching your PostgreSQL major, Python version, and platform
from [Releases](https://github.com/DocumentDrivenDX/pgserver/releases):

```sh
uv pip install /path/to/pgserver_pg17-17.11.0-<python-and-platform-tags>.whl
# A full GitHub Release asset URL works in place of the local path.
```

No PyPI publication. Release tags are recorded in `build-versions.json`.
They normally use `pg<version>-pgv<version>`; a revision suffix distinguishes
changes to packaging for the same native versions. The expanded PG18 platform
set uses `pg18.6-pgv0.8.6-r1` to preserve the initial tag's history.

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

1. Update the corresponding version, checksum, distribution version and release
   tag in `build-versions.json`. Keep the Makefile and pyproject default PG18
   values aligned with that entry.
2. Obtain PostgreSQL source checksums from its official release directory and
   independently review pgvector source checksums when updating pgvector.
3. Run the nine-job build matrix. Installed-wheel tests check binary versions,
   bundled licenses, pgvector loading, Unix sockets, disabled TCP, and cleanup,
   in addition to the upstream test suite.
4. Dispatch the workflow from `main` with `publish=true`. Only after all nine
   platform/version jobs pass will it create three separate GitHub Releases,
   with wheels, checksums and GitHub build-provenance attestations. Each release
   tag targets the exact workflow commit. Choose new tags for subsequent updates.

PostgreSQL minor releases normally arrive roughly quarterly; consult its
[release schedule](https://www.postgresql.org/developer/roadmap/).

## Licenses and changes

The Python wrapper retains upstream Apache-2.0 [LICENSE](LICENSE), attribution,
and history. [NOTICE](NOTICE) identifies fork changes. PostgreSQL and pgvector
use the PostgreSQL license; their source license texts are included in wheels.
The fork keeps the caller API and changes build versions, checksum validation,
portable pgvector flags, relocatable native libraries, license packaging,
and release automation.
