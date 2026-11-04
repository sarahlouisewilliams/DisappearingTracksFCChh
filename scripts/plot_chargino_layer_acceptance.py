
#!/usr/bin/env python3

import argparse
import math
import os

import matplotlib.pyplot as plt
import numpy as np
from podio import root_io


LIFETIMES = [0.2, 1.0, 2.0, 5.0, 10.0]


def identify_barrel_layer(r_mm):
    """Provisional barrel-layer identification from hit radius."""
    windows = [
        (20.0, 35.0),
        (55.0, 70.0),
        (95.0, 110.0),
        (145.0, 160.0),
        (255.0, 275.0),
    ]

    for layer, (rmin, rmax) in enumerate(windows, start=1):
        if rmin <= r_mm < rmax:
            return layer

    return None


def calculate_acceptance(filename, max_events=None):
    reader = root_io.Reader(filename)

    counts = {
        "total": 0,
        "4hits": 0,
        "5hits": 0,
        "4layers": 0,
        "5layers": 0,
    }

    for event in reader.get("events"):
        if max_events is not None and counts["total"] >= max_events:
            break

        counts["total"] += 1

        particles = [
            p for p in event.get("SimParticleSecondaries")
            if abs(p.getPDG()) == 1000024
        ]

        if len(particles) != 1:
            continue

        g4id = particles[0].getSimulatorStatus()

        try:
            hits = [
                hit for hit in event.get("TrackerBarrelReadout")
                if hit.getQuality() == g4id
            ]
        except Exception:
            hits = []

        layers = set()

        for hit in hits:
            pos = hit.getPosition()
            r = math.hypot(pos.x, pos.y)

            layer = identify_barrel_layer(r)

            if layer is not None:
                layers.add(layer)

        counts["4hits"] += len(hits) >= 4
        counts["5hits"] += len(hits) >= 5
        counts["4layers"] += {1, 2, 3, 4}.issubset(layers)
        counts["5layers"] += {1, 2, 3, 4, 5}.issubset(layers)

    n = counts["total"]

    if n == 0:
        raise RuntimeError(f"No events found in {filename}")

    return {
        key: counts[key] / n
        for key in ("4hits", "5hits", "4layers", "5layers")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="results/lifetime_scan",
    )
    parser.add_argument(
        "--output",
        default="results/lifetime_scan/layer_acceptance.png",
    )
    parser.add_argument("--events", type=int, default=None)
    args = parser.parse_args()

    results = {
        "4hits": [],
        "5hits": [],
        "4layers": [],
        "5layers": [],
    }

    for tau in LIFETIMES:
        #tag = f'tau{format(float(tau), "g").replace(".", "p")}ns'
        tag = f'tau{str(tau).replace(".", "p")}ns'
        filename = os.path.join(
            args.input_dir,
            f"chargino_{tag}_SIM.root",
        )

        print(f"Processing {filename}")

        acceptance = calculate_acceptance(
            filename,
            max_events=args.events,
        )

        print(f"  tau = {tau} ns")
        for key, value in acceptance.items():
            print(f"    {key:8s}: {value:.4f}")
            results[key].append(value)

    plt.figure(figsize=(8, 5.5))

    styles = [
        ("4hits", ">=4 hits", "o", "-"),
        ("4layers", "First 4 layers", "s", "--"),
        ("5hits", ">=5 hits", "^", "-"),
        ("5layers", "First 5 layers", "D", "--"),
    ]

    for key, label, marker, linestyle in styles:
        plt.plot(
            LIFETIMES,
            results[key],
            marker=marker,
            linestyle=linestyle,
            linewidth=2,
            label=label,
        )

    plt.xlabel("Chargino proper lifetime [ns]")
    plt.ylabel("Acceptance")
    plt.title("Chargino hit and layer acceptance")
    plt.ylim(0, 1)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    plt.savefig(args.output, dpi=180)

    print(f"\nSaved {args.output}")


if __name__ == "__main__":
    main()
