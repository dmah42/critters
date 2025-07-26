#!/bin/bash

set -e

source .venv/bin/activate

export FLASK_APP=run_web.py
export FLASK_DEBUG=1

flask run --host=localhost --port=5050
