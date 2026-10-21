#!/usr/bin/env bash
set -euo pipefail
source setup.sh
source build.sh
k4run options/run_chargino_fcchh.py
python3 scripts/inspect_file.py chargino_fcchh_SIM.root
python3 scripts/check_decay.py chargino_fcchh_SIM.root
