#!/bin/bash

set -e

source .venv/bin/activate

TIMER=5.0

if [ $# -eq 1 ]; then
  TIMER=$1
fi

python run_sim.py -t $TIMER
