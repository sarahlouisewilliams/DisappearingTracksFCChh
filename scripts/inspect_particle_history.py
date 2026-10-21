#!/usr/bin/env python3

import sys
from podio import root_io

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} file.root")
    sys.exit(1)

filename = sys.argv[1]

reader = root_io.Reader(filename)

for iev, event in enumerate(reader.get("events")):

    particles = event.get("SimParticleSecondaries")

    print(f"\n=== Event {iev} ===")
    print(f"N particles = {len(particles)}")

    print(
        f"{'i':>4} {'PDG':>10} {'G4 ID':>7} "
        f"{'p [GeV]':>12} "
        f"{'vx [mm]':>11} {'vy [mm]':>11} {'vz [mm]':>11}"
    )
    print("-" * 72)

    for i, p in enumerate(particles):

        mom = p.getMomentum()
        pmag = (mom.x**2 + mom.y**2 + mom.z**2)**0.5

        v = p.getVertex()

        print(
            f"{i:4d} "
            f"{p.getPDG():10d} "
            f"{p.getSimulatorStatus():7d} "
            f"{pmag:12.4f} "
            f"{v.x:11.4f} "
            f"{v.y:11.4f} "
            f"{v.z:11.4f}"
        )

    # First event only for now
    break