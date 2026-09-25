#!/usr/bin/env bash
set -euo pipefail

if [ ! -x ".venv/bin/pytest" ]; then
    echo "Run ./dev/setup.sh first."
    exit 1
fi

if [ ! -d "tests" ]; then
    echo "No tests directory."
    exit 0
fi

exec .venv/bin/pytest "$@"
