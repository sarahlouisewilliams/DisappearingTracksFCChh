#!/usr/bin/env python3

import argparse
import math
import podio.root_io


def cluster_radii(radii, tolerance=5.0):
    """
    Group hits with similar radius into approximate radial surfaces.

    This is only a diagnostic; it is NOT a replacement for decoding
    the DD4hep cellID.
    """
    if not radii:
        return []

    radii = sorted(radii)

    clusters = [[radii[0]]]

    for r in radii[1:]:
        if abs(r - clusters[-1][-1]) < tolerance:
            clusters[-1].append(r)
        else:
            clusters.append([r])

    return [
        sum(cluster) / len(cluster)
        for cluster in clusters
    ]


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-n", "--events", type=int, default=-1)
    args = parser.parse_args()

    reader = podio.root_io.Reader(args.input)

    print(
        f"{'evt':>5} "
        f"{'Nhits':>7} "
        f"{'rmin [mm]':>12} "
        f"{'rmax [mm]':>12} "
        f"{'N radial':>9} "
        f"radial surfaces [mm]"
    )

    print("-" * 100)

    for ievt, frame in enumerate(reader.get("events")):

        if args.events >= 0 and ievt >= args.events:
            break

        if "TrackerBarrelReadout" not in frame.getAvailableCollections():
            continue

        hits = frame.get("TrackerBarrelReadout")

        radii = []

        for hit in hits:
            pos = hit.getPosition()
            r = math.hypot(pos.x, pos.y)
            radii.append(r)

        surfaces = cluster_radii(radii)

        if radii:
            rmin = min(radii)
            rmax = max(radii)
        else:
            rmin = 0.0
            rmax = 0.0

        surface_string = " ".join(
            f"{r:.1f}" for r in surfaces
        )

        print(
            f"{ievt:5d} "
            f"{len(radii):7d} "
            f"{rmin:12.1f} "
            f"{rmax:12.1f} "
            f"{len(surfaces):9d} "
            f"{surface_string}"
        )


if __name__ == "__main__":
    main()