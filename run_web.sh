#!/bin/bash

set -e

source .venv/bin/activate

export FLASK_APP=run_web.py
export FLASK_DEBUG=1

flask run --host=0.0.0.0 --port=5050
