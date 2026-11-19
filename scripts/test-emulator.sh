#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -x .venv/bin/python ]]; then
    printf '%s\n' "Create the .venv and install requirements.txt before running the lab." >&2
    exit 1
fi

source scripts/use-emulator.sh "${AWS_EMULATOR_PORT:-9297}"
exec .venv/bin/python -X faulthandler -m pytest "$@"
