#!/usr/bin/env bash

source /cvmfs/sw.hsf.org/key4hep/setup.sh

# Register this local project with the Key4hep development environment.
# This is the workflow recommended by current Key4hep project templates.
k4_local_repo

if [[ ! -d external/FCCSW ]]; then
  git clone --depth 1 https://github.com/HEP-FCC/FCCSW.git external/FCCSW
fi
export PYTHONPATH="$PWD/external/FCCSW:${PYTHONPATH:-}"

if [[ ! -d external/FCCDetectors ]]; then
  git clone --depth 1 https://github.com/HEP-FCC/FCCDetectors.git external/FCCDetectors
fi
export FCCDETECTORS="$PWD/external/FCCDetectors"

echo "KEY4HEP_STACK=${KEY4HEP_STACK:-<not set>}"
echo "FCCDETECTORS=$FCCDETECTORS"
