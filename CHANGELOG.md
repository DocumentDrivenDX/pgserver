# Changelog

## Unreleased
- Release workflow publishes `pgserver-pg16`, `pgserver-pg17` and `pgserver-pg18` to PyPI
  (trusted publishing) on a `pgserver-pgNN-vX.Y.Z` tag. Wheels now target CPython 3.11-3.14
  (3.10 dropped). Existing 16.15.1 / 17.11.1 / 18.6.1 wheels can be backfilled to PyPI unchanged.
- PRs run Linux-only CI; macOS wheels are built only by the release workflow.

## 18.6.1 / 17.11.1 / 16.15.1
- GitHub Release wheels for PostgreSQL 18.6, 17.11 and 16.15 with pgvector 0.8.6
  (Linux x86_64/aarch64, macOS arm64, CPython 3.10-3.13). Tags `pg18.6-pgv0.8.6-r2`,
  `pg17.11-pgv0.8.6-r1`, `pg16.15-pgv0.8.6-r1`.
