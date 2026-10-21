#!/usr/bin/env python3
"""Quick validation: print chargino MCParticle endpoints and daughters."""
import argparse, math
import podio.root_io

ap = argparse.ArgumentParser()
ap.add_argument("input")
args = ap.parse_args()

reader = podio.root_io.Reader(args.input)
n = 0
for frame in reader.get("events"):
    for p in frame.get("GenParticles"):
        if abs(p.getPDG()) != 1000024:
            continue
        ep = p.getEndpoint()
        r = math.hypot(ep.x, ep.y)
        daughters = [d.getPDG() for d in p.getDaughters()]
        print(f"PDG={p.getPDG():+d} endpoint: r={r:.3f} mm z={ep.z:.3f} mm daughters={daughters}")
        n += 1
print(f"Found {n} chargino MCParticles")
