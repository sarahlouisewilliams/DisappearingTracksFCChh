import ROOT
import os

ROOT.gSystem.Load("libDDCore")

det = ROOT.dd4hep.Detector.getInstance()

geometry = os.path.join(
    os.environ["FCCDETECTORS"],
    "Detector/DetFCChhBaseline1/compact/FCChh_DectMaster.xml"
)

det.fromXML(geometry)

readout = det.readout("TrackerBarrelReadout")
decoder = readout.idSpec().decoder()

cellids = [
    129575275838153728,
    135534567925979152,
    135521743153756192,
]

for cellid in cellids:
    print(
        cellid,
        "system =", decoder.get(cellid, "system"),
        "layer =", decoder.get(cellid, "layer"),
        "module =", decoder.get(cellid, "module"),
    )