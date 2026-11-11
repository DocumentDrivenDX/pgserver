#!/usr/bin/env bash
set -euo pipefail
PROJECT=$1
# Abort promptly on failure; bound tests even when a child never answers a queue.
python -m pytest -x -v --timeout=90 --timeout-method=thread --log-cli-level=INFO "$PROJECT/tests"
# The README quickstart must keep working against the installed wheel.
python "$PROJECT/.github/run_quickstart.py" "$PROJECT/README.md"
