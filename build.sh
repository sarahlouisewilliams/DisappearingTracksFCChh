#!/usr/bin/env bash

rm -rf build install
mkdir -p build install

cmake -S . -B build \
  -DCMAKE_INSTALL_PREFIX="$PWD/install" \
  -G Ninja

cmake --build build
cmake --install build

# Key4hep/Gaudi local projects do not necessarily create install/setup.sh.
# k4_local_repo updates PATH/PYTHONPATH/LD_LIBRARY_PATH for the local build.
k4_local_repo

echo
echo "Build complete."
echo "Now run:"
echo "  k4run options/run_chargino_fcchh.py"
