cmake_minimum_required(VERSION 3.15)
project(FCChhDisappearingTrackTutorial VERSION 0.3.0 LANGUAGES CXX)

find_package(Gaudi REQUIRED)
find_package(Geant4 REQUIRED)
find_package(k4SimGeant4 REQUIRED)

include(${Geant4_USE_FILE})

set(K4SIMGEANT4_ROOT
    "/cvmfs/sw.hsf.org/key4hep/releases/2026-04-08/x86_64-almalinux9-gcc14.2.0-opt/k4simgeant4/0.1.0pre17-tzo63b"
)

gaudi_add_module(CharginoPhysics
  SOURCES
    src/SimG4CharginoFtfpBert.cpp

  LINK
    Gaudi::GaudiKernel
    ${Geant4_LIBRARIES}
)

target_include_directories(CharginoPhysics PRIVATE
    ${K4SIMGEANT4_ROOT}/include
)