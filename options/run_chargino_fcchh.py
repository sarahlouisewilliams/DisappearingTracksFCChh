"""
Generate and fully simulate decaying charginos in the current FCC-hh setup.

Default model:
  m(chi0) = 3000.000 GeV
  m(chi+) = m(chi-) = 3000.165 GeV
  tau(chi+/-) = 0.2 ns
  chi+ -> chi0 pi+
  chi- -> chi0 pi-

For a stable-chargino geometry study set STABLE_CHARGINO=True.
"""

import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

from Gaudi.Configuration import INFO
from GaudiKernel import SystemOfUnits as units
from GaudiKernel import PhysicalConstants as constants
from k4FWCore import ApplicationMgr, IOSvc
from Configurables import (
    EventDataSvc,
    MomentumRangeParticleGun,
    GenAlg,
    HepMCToEDMConverter,
    SimG4Svc,
    SimG4PrimariesFromEdmTool,
    SimG4CharginoFtfpBert,
)

from detector_fcc_hh_fixed_disTrack import geantsim

# ----------------------------------------------------------------------
# Tutorial settings
# ----------------------------------------------------------------------
N_EVENTS = 1000
OUTPUT = "chargino_decay_truth_SIM.root"

NEUTRALINO_MASS_GEV = 3000.0
MASS_SPLITTING_GEV = 0.165
CHARGINO_LIFETIME_NS = 0.2
STABLE_CHARGINO = False

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
#gun.MomentumMin = 100.0 * units.GeV
#gun.MomentumMax = 1000.0 * units.GeV
gun.MomentumMin = 1000.0 * units.GeV
gun.MomentumMax = 1000.0 * units.GeV
#gun.ThetaMin = 0.0
#gun.ThetaMax = constants.pi
gun.ThetaMin = 1.50
gun.ThetaMax = 1.64

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


geantservice = SimG4Svc("SimG4Svc")
geantservice.detector = "SimG4DD4hepDetector"
# SimG4Svc resolves the tool by type/name. Use the configured instance above.
geantservice.physicslist = physics

from Configurables import SimG4FullSimActions

actions = SimG4FullSimActions("FullSimActions")
actions.enableHistory = True
actions.energyCut = 0.0

geantservice.actions = actions

app.ExtSvc += [geantservice]

geantsim.eventProvider = SimG4PrimariesFromEdmTool("EdmConverter")
geantsim.eventProvider.GenParticles.Path = "GenParticles"

app.TopAlg += [geantsim]

iosvc = IOSvc()
iosvc.Output = OUTPUT
iosvc.outputCommands = ["keep *"]

