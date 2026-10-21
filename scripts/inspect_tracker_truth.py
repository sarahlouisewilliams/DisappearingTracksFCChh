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

    # Build:
    #
    #    Geant4 track ID -> MCParticle
    #
    particle_by_trackid = {}

    for p in particles:
        trackid = p.getSimulatorStatus()
        particle_by_trackid[trackid] = p

    print(f"\n=== Event {iev} ===")

    for collection_name in [
        "TrackerBarrelReadout",
        "TrackerEndcapReadout",
    ]:

        hits = event.get(collection_name)

        print(f"\n{collection_name}: {len(hits)} hits")

        print(
            f"{'i':>4} "
            f"{'G4 ID':>7} "
            f"{'PDG':>10} "
            f"{'x [mm]':>10} "
            f"{'y [mm]':>10} "
            f"{'z [mm]':>10} "
            f"{'r [mm]':>10}"
        )

        print("-" * 70)

        for i, hit in enumerate(hits):

            trackid = hit.getQuality()

            particle = particle_by_trackid.get(trackid)

            if particle is not None:
                pdg = particle.getPDG()
            else:
                pdg = 0

            pos = hit.getPosition()

            r = (pos.x**2 + pos.y**2)**0.5

            print(
                f"{i:4d} "
                f"{trackid:7d} "
                f"{pdg:10d} "
                f"{pos.x:10.3f} "
                f"{pos.y:10.3f} "
                f"{pos.z:10.3f} "
                f"{r:10.3f}"
            )

    # first event only
    break