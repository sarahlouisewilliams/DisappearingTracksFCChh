#!/usr/bin/env python3

import argparse
import math

import podio.root_io


parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("--events", type=int, default=10)
args = parser.parse_args()

reader = podio.root_io.Reader(args.input)

for ievt, frame in enumerate(reader.get("events")):

    if ievt >= args.events:
        break

    print()
    print("=" * 80)
    print(f"Event {ievt}")
    print("=" * 80)

    for name in frame.getAvailableCollections():

        collection = frame.get(name)

        # Look only at collections containing SimTrackerHits
        if len(collection) == 0:
            continue

        first = collection[0]

        if type(first).__name__ != "SimTrackerHit":
            continue

        print()
        print(f"Collection: {name}")
        print(f"Number of hits: {len(collection)}")

        for ihit, hit in enumerate(collection):

            pos = hit.getPosition()

            r = math.sqrt(
                pos.x * pos.x +
                pos.y * pos.y
            )

            particle = hit.getParticle()

            if particle.isAvailable():
                pdg = particle.getPDG()
                oid = particle.getObjectID()

                particle_info = (
                    f"PDG={pdg:9d} "
                    f"MCParticle=({oid.collectionID},{oid.index})"
                )
            else:
                particle_info = "no MCParticle link"

            print(
                f"  hit {ihit:4d}: "
                f"r={r:9.3f} mm "
                f"z={pos.z:9.3f} mm "
                f"{particle_info}"
            )