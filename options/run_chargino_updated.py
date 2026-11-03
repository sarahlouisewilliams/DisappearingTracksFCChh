"""
Generate and fully simulate decaying charginos in the current FCC-hh setup.

Parameters can be overridden with environment variables, for example:

  CHARGINO_LIFETIME_NS=1.0 MOMENTUM_MIN_GEV=500 MOMENTUM_MAX_GEV=1500 \
  N_EVENTS=10000 OUTPUT=chargino_tau1ns_SIM.root \
  k4run options/run_chargino_fcchh_updated.py

For a stable-chargino geometry study set STABLE_CHARGINO=True.
"""

import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

from Gaudi.Configuration import INFO
from GaudiKernel import SystemOfUnits as units
from k4FWCore import ApplicationMgr, IOSvc
from Configurables import (
    EventDataSvc,
    MomentumRangeParticleGun,
    GenAlg,
    HepMCToEDMConverter,
    SimG4Svc,
    SimG4PrimariesFromEdmTool,
    SimG4CharginoFtfpBert,
    SimG4FullSimActions,
)

from detector_fcc_hh_fixed_disTrack import geantsim

# ----------------------------------------------------------------------
# Tutorial settings -- overridable from the shell
# ----------------------------------------------------------------------
N_EVENTS = int(os.environ.get("N_EVENTS", "1000"))
OUTPUT = os.environ.get("OUTPUT", "chargino_decay_truth_SIM.root")

NEUTRALINO_MASS_GEV = float(os.environ.get("NEUTRALINO_MASS_GEV", "3000.0"))
MASS_SPLITTING_GEV = float(os.environ.get("MASS_SPLITTING_GEV", "0.165"))
CHARGINO_LIFETIME_NS = float(os.environ.get("CHARGINO_LIFETIME_NS", "0.2"))

STABLE_CHARGINO = (
    os.environ.get("STABLE_CHARGINO", "False").lower()
    in ("true", "1", "yes")
)

MOMENTUM_MIN_GEV = float(os.environ.get("MOMENTUM_MIN_GEV", "1000.0"))
MOMENTUM_MAX_GEV = float(os.environ.get("MOMENTUM_MAX_GEV", "1000.0"))
THETA_MIN = float(os.environ.get("THETA_MIN", "1.50"))
THETA_MAX = float(os.environ.get("THETA_MAX", "1.64"))

print("============================================")
print(" Chargino FCC-hh simulation")
print("============================================")
print(f"N events             = {N_EVENTS}")
print(f"Output               = {OUTPUT}")
print(f"Neutralino mass      = {NEUTRALINO_MASS_GEV} GeV")
print(f"Mass splitting       = {MASS_SPLITTING_GEV} GeV")
print(f"Chargino lifetime    = {CHARGINO_LIFETIME_NS} ns")
print(f"Stable chargino      = {STABLE_CHARGINO}")
print(f"Momentum range       = {MOMENTUM_MIN_GEV} -- {MOMENTUM_MAX_GEV} GeV")
print(f"Theta range          = {THETA_MIN} -- {THETA_MAX} rad")
print("============================================")

# ----------------------------------------------------------------------
# Framework
# ----------------------------------------------------------------------
app = ApplicationMgr()
app.EvtSel = "NONE"
app.EvtMax = N_EVENTS
app.OutputLevel = INFO
app.ExtSvc += ["RndmGenSvc", EventDataSvc("EventDataSvc")]

# ----------------------------------------------------------------------
# Generator
# ----------------------------------------------------------------------
gun = MomentumRangeParticleGun("CharginoGun")
gun.PdgCodes = [1000024, -1000024]
gun.MomentumMin = MOMENTUM_MIN_GEV * units.GeV
gun.MomentumMax = MOMENTUM_MAX_GEV * units.GeV
gun.ThetaMin = THETA_MIN
gun.ThetaMax = THETA_MAX

gen = GenAlg("CharginoGenerator")
gen.SignalProvider = gun
gen.hepmc.Path = "hepmc"
app.TopAlg += [gen]

converter = HepMCToEDMConverter("Converter")
converter.hepmc.Path = "hepmc"
converter.GenParticles.Path = "GenParticles"
app.TopAlg += [converter]

# ----------------------------------------------------------------------
# Custom FTFP_BERT + chargino/neutralino physics
# ----------------------------------------------------------------------
physics = SimG4CharginoFtfpBert("PhysicsList")
physics.NeutralinoMassGeV = NEUTRALINO_MASS_GEV
physics.CharginoPlusMassGeV = NEUTRALINO_MASS_GEV + MASS_SPLITTING_GEV
physics.CharginoMinusMassGeV = NEUTRALINO_MASS_GEV + MASS_SPLITTING_GEV
physics.CharginoPlusLifetimeNs = CHARGINO_LIFETIME_NS
physics.CharginoMinusLifetimeNs = CHARGINO_LIFETIME_NS
physics.StableChargino = STABLE_CHARGINO

# ----------------------------------------------------------------------
# Geant4 service
# ----------------------------------------------------------------------
geantservice = SimG4Svc("SimG4Svc")
geantservice.detector = "SimG4DD4hepDetector"

# Use the configured instance; do not replace this with a type/name string.
geantservice.physicslist = physics

# Enable Geant4 particle history. The history saver itself is already
# configured in detector_fcc_hh_fixed_disTrack.py; do not add a duplicate.
actions = SimG4FullSimActions("FullSimActions")
actions.enableHistory = True
actions.energyCut = 0.0
geantservice.actions = actions

app.ExtSvc += [geantservice]

# ----------------------------------------------------------------------
# Geant4 simulation
# ----------------------------------------------------------------------
geantsim.eventProvider = SimG4PrimariesFromEdmTool("EdmConverter")
geantsim.eventProvider.GenParticles.Path = "GenParticles"
app.TopAlg += [geantsim]

# ----------------------------------------------------------------------
# EDM4hep output
# ----------------------------------------------------------------------
iosvc = IOSvc()
iosvc.Output = OUTPUT
iosvc.outputCommands = ["keep *"]
