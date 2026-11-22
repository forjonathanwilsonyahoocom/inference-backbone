#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python -m pip install -q -e ".[test]"
.venv/bin/python -m pip install -q -e ../contracts -e ../observability
.venv/bin/python -m pytest -s
