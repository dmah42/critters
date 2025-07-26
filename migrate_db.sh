#!/bin/bash

set -e

source .venv/bin/activate

export FLASK_APP=run_web.py
export FLASK_DEBUG=1

if [ $# -eq 0 ]; then
  echo "Usage: $0 \"message\""
  exit 1
fi

MESSAGE=$1

flask db migrate -m "$1"
flask db upgrade
