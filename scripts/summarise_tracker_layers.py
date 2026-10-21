#!/usr/bin/env python3

import argparse
import math
import os
import ROOT
import podio.root_io


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-n", "--events", type=int, default=-1)
    args = parser.parse_args()

    # ------------------------------------------------------------
    # Load FCC-hh geometry
    # ------------------------------------------------------------

    ROOT.gSystem.Load("libDDCore")

    det = ROOT.dd4hep.Detector.getInstance()

    geometry = os.path.join(
        os.environ["FCCDETECTORS"],
        "Detector/DetFCChhBaseline1/compact/FCChh_DectMaster.xml"
    )

    det.fromXML(geometry)

    readout = det.readout("TrackerBarrelReadout")
    decoder = readout.idSpec().decoder()

    # ------------------------------------------------------------
    # Open EDM4hep file
    # ------------------------------------------------------------

    reader = podio.root_io.Reader(args.input)

    print()
    print(
        f"{'evt':>5} "
        f"{'Nhits':>7} "
        f"{'Nlayers':>8} "
        f"{'first':>7} "
        f"{'last':>7} "
        f"{'rmax [mm]':>12} "
        f"layers"
    )
    print("-" * 100)

    for ievt, frame in enumerate(reader.get("events")):

        if args.events >= 0 and ievt >= args.events:
            break

        if "TrackerBarrelReadout" not in frame.getAvailableCollections():
            continue

        hits = frame.get("TrackerBarrelReadout")

        layers = set()
        rmax = 0.0

        for hit in hits:

            cellid = hit.getCellID()

            system = int(decoder.get(cellid, "system"))
            layer = int(decoder.get(cellid, "layer"))

            # Keep (system,layer), since layer numbering could
            # in principle be reused between tracker systems.
            layers.add((system, layer))

            pos = hit.getPosition()
            r = math.hypot(pos.x, pos.y)

            rmax = max(rmax, r)

        layers = sorted(layers)

        if layers:
            first_layer = layers[0]
            last_layer = layers[-1]
        else:
            first_layer = None
            last_layer = None

        layer_string = " ".join(
            f"{system}:{layer}"
            for system, layer in layers
        )

        print(
            f"{ievt:5d} "
            f"{len(hits):7d} "
            f"{len(layers):8d} "
            f"{str(first_layer):>7} "
            f"{str(last_layer):>7} "
            f"{rmax:12.1f} "
            f"{layer_string}"
        )


if __name__ == "__main__":
    main()