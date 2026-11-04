
#!/usr/bin/env python3

import argparse
import math
from podio import root_io


def identify_barrel_layer(r_mm):
    """Provisional layer identification using hit radius."""
    windows = [
        (20.0, 35.0),    # Layer 1
        (55.0, 70.0),    # Layer 2
        (95.0, 110.0),   # Layer 3
        (145.0, 160.0),  # Layer 4
        (255.0, 275.0),  # Layer 5
    ]

    for layer, (rmin, rmax) in enumerate(windows, start=1):
        if rmin <= r_mm < rmax:
            return layer

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--events", type=int, default=None)
    args = parser.parse_args()

    reader = root_io.Reader(args.input)

    n_events = 0
    n_4hits = 0
    n_5hits = 0
    n_4layers = 0
    n_5layers = 0

    for event in reader.get("events"):
        if args.events is not None and n_events >= args.events:
            break

        n_events += 1

        # Identify the generated chargino
        particles = [
            p for p in event.get("SimParticleSecondaries")
            if abs(p.getPDG()) == 1000024
        ]

        if len(particles) != 1:
            continue

        g4id = particles[0].getSimulatorStatus()

        # Collect associated barrel hits
        hits = [
            hit for hit in event.get("TrackerBarrelReadout")
            if hit.getQuality() == g4id
        ]

        n_hits = len(hits)
        hit_layers = set()

        for hit in hits:
            pos = hit.getPosition()
            r = math.hypot(pos.x, pos.y)

            layer = identify_barrel_layer(r)
            if layer is not None:
                hit_layers.add(layer)

        passes_4layers = {1, 2, 3, 4}.issubset(hit_layers)
        passes_5layers = {1, 2, 3, 4, 5}.issubset(hit_layers)

        n_4hits += n_hits >= 4
        n_5hits += n_hits >= 5
        n_4layers += passes_4layers
        n_5layers += passes_5layers

    print(f"Events: {n_events}")

    if n_events == 0:
        return

    print(f">=4 hits:   {n_4hits/n_events:.4f}")
    print(f">=5 hits:   {n_5hits/n_events:.4f}")
    print(f"4 layers:   {n_4layers/n_events:.4f}")
    print(f"5 layers:   {n_5layers/n_events:.4f}")


if __name__ == "__main__":
    main()
