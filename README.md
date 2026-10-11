# PostgreSQL 18 wheels for pgserver

DocumentDrivenDX fork of [orm011/pgserver](https://github.com/orm011/pgserver),
for applications that need an embedded PostgreSQL 18 server, including tests
that match the PostgreSQL major version used by Lakebase. This does not claim
full Lakebase feature parity.

The distribution is `pgserver-pg18` version `18.6.0`; the Python import remains
`pgserver`. It bundles PostgreSQL **18.6** and pgvector **0.8.6**. Do not install
it alongside the upstream `pgserver` distribution, which owns the same imports.
Ordinary wheel installation does not compile PostgreSQL.

## Install

Download the wheel matching your Python and platform from
[Releases](https://github.com/DocumentDrivenDX/pgserver/releases), then run:

```sh
uv pip install /path/to/pgserver_pg18-18.6.0-<python-and-platform-tags>.whl
# A full GitHub Release asset URL works in place of the local path.
```

Release tags use `pg18.6-pgv0.8.6`. CI targets macOS arm64 and x86_64
(macOS 14 minimum), and Linux x86_64 (manylinux). Wheel availability and
verification are determined by the successful workflow artifacts; a target
is not a support claim before its build and tests pass. No PyPI publication.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import pgserver

with TemporaryDirectory(prefix="pg18-") as root:
    with pgserver.get_server(Path(root) / "data") as server:
        print(server.get_uri())
```

On Unix the upstream API disables TCP and selects a Unix socket directory.
Use a separate data directory per test worker and keep one server alive per
worker. See [upstream usage](UPSTREAM-README.md).

## Build and update

`make` builds native binaries once; `python -m build --wheel` packages them.
Native build prerequisites include a C compiler, make, Python 3, curl, bison,
flex, and zlib development headers. Source installs require `make` first.

1. Update `POSTGRES_VERSION` / `POSTGRES_SHA256` and `PGVECTOR_TAG` /
   `PGVECTOR_SHA256` in `pgbuild/Makefile`. Both can be overridden with make
   variables, but matching trusted checksums are required.
2. Obtain the PostgreSQL checksum from its official release source directory
   and independently review the pgvector release and its source checksum.
3. Bump the distribution version in `pyproject.toml`; rebuild from a clean
   checkout to avoid reusing binaries from a different source version.
4. Run the build workflow, inspect all three platform tests, then push the
   matching `pg<version>-pgv<version>` tag. The workflow attaches wheels,
   checksums and GitHub build-provenance attestations to the release.

PostgreSQL minor releases normally arrive roughly quarterly; consult its
[release schedule](https://www.postgresql.org/developer/roadmap/) and
[18.6 notes](https://www.postgresql.org/docs/release/18.6/).

## Licenses and changes

The Python wrapper retains upstream Apache-2.0 [LICENSE](LICENSE), attribution,
and history. [NOTICE](NOTICE) identifies fork changes. PostgreSQL and pgvector
use the PostgreSQL license; their source license texts are included in wheels.
The fork keeps the caller API and changes build versions, checksum validation,
portable pgvector flags, license packaging, and release automation.
