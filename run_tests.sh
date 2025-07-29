#!/bin/bash

set -e

source .venv/bin/activate

export FLASK_APP=run_web.py
export FLASK_DEBUG=1

python -m unittest discover