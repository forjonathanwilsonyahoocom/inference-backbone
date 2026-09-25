#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv

. .venv/bin/activate

python -m pip install --upgrade pip

python -m pip install -e ./contracts
python -m pip install -e ./observability

python -m pip install -r ./worker-agent/requirements.txt

python -m pip install "pytest>=8"

echo
echo "Development environment ready."
echo "Activate with:"
echo "  source .venv/bin/activate"
