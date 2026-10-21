#!/usr/bin/env python3

import argparse
import math
from collections import defaultdict

import ROOT
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from podio import root_io


CHARGINO_PDG = 1000024
NEUTRALINO_PDG = 1000022
PION_PDG = 211


# ----------------------------------------------------------------------
# Geometry / cellID decoding
# ----------------------------------------------------------------------

def setup_geometry():
    """
    Load the FCC-hh detector geometry and construct DD4hep decoders
    for the barrel and endcap tracker readouts.
    """

    ROOT.gSystem.Load("libDDCore")

    detector = ROOT.dd4hep.Detector.getInstance()

    import os

    geometry = os.path.join(
        os.environ["FCCDETECTORS"],
        "Detector/DetFCChhBaseline1/compact/FCChh_DectMaster.xml",
    )

    detector.fromXML(geometry)

    decoders = {}

    for readout_name in [
        "TrackerBarrelReadout",
        "TrackerEndcapReadout",
    ]:
        readout = detector.readout(readout_name)
        decoders[readout_name] = readout.idSpec().decoder()

    return detector, decoders


def decode_hit(cellid, collection_name, decoder):
    """
    Decode the useful layer information from an FCC-hh tracker cellID.

    Barrel:
        system, layer

    Endcap:
        system, posneg, disc
    """

    if collection_name == "TrackerBarrelReadout":

        system = int(decoder.get(cellid, "system"))
        layer = int(decoder.get(cellid, "layer"))

        return {
            "region": "barrel",
            "system": system,
            "layer": layer,
            "disc": -1,
            "posneg": 0,
            "layer_key": f"B:{system}:{layer}",
        }

    elif collection_name == "TrackerEndcapReadout":

        system = int(decoder.get(cellid, "system"))
        posneg = int(decoder.get(cellid, "posneg"))
        disc = int(decoder.get(cellid, "disc"))

        return {
            "region": "endcap",
            "system": system,
            "layer": -1,
            "disc": disc,
            "posneg": posneg,
            "layer_key": f"E:{system}:{posneg}:{disc}",
        }

    raise RuntimeError(f"Unknown tracker collection {collection_name}")


# ----------------------------------------------------------------------
# MC truth helpers
# ----------------------------------------------------------------------

def momentum_magnitude(particle):
    p = particle.getMomentum()

    return math.sqrt(
        p.x * p.x +
        p.y * p.y +
        p.z * p.z
    )


def particle_eta(particle):
    p = particle.getMomentum()

    pt = math.sqrt(p.x * p.x + p.y * p.y)
    pabs = math.sqrt(pt * pt + p.z * p.z)

    if pabs == abs(p.z):
        return math.copysign(float("inf"), p.z)

    return 0.5 * math.log(
        (pabs + p.z) /
        (pabs - p.z)
    )


def particle_pt(particle):
    p = particle.getMomentum()

    return math.sqrt(
        p.x * p.x +
        p.y * p.y
    )


def find_chargino(particles):
    """
    Single-chargino particle-gun sample:
    find the unique chargino in SimParticleSecondaries.
    """

    candidates = [
        p for p in particles
        if abs(p.getPDG()) == CHARGINO_PDG
    ]

    if len(candidates) != 1:
        return None

    return candidates[0]


def find_decay_vertex(particles, chargino):
    """
    Find the chargino decay vertex using the neutralino and charged pion.

    Current SimG4 particle-history code does not persist parent/daughter
    relations, so for the present single-chargino sample we identify the
    neutralino and pion and require their production vertices to agree.

    Returns:
        x, y, z, r

    or None if no suitable pair can be identified.
    """

    chargino_sign = 1 if chargino.getPDG() > 0 else -1

    # chi+ -> chi0 + pi+
    # chi- -> chi0 + pi-
    expected_pion_pdg = chargino_sign * PION_PDG

    neutralinos = [
        p for p in particles
        if p.getPDG() == NEUTRALINO_PDG
    ]

    pions = [
        p for p in particles
        if p.getPDG() == expected_pion_pdg
    ]

    if len(neutralinos) != 1 or len(pions) != 1:
        return None

    neutralino = neutralinos[0]
    pion = pions[0]

    vn = neutralino.getVertex()
    vp = pion.getVertex()

    separation = math.sqrt(
        (vn.x - vp.x)**2 +
        (vn.y - vp.y)**2 +
        (vn.z - vp.z)**2
    )

    # Vertices should be identical for the two-body decay.
    # 1 micron tolerance is already generous here.
    if separation > 1.0e-3:
        return None

    x = 0.5 * (vn.x + vp.x)
    y = 0.5 * (vn.y + vp.y)
    z = 0.5 * (vn.z + vp.z)

    r = math.sqrt(x*x + y*y)

    return {
        "x": x,
        "y": y,
        "z": z,
        "r": r,
        "neutralino_trackid": neutralino.getSimulatorStatus(),
        "pion_trackid": pion.getSimulatorStatus(),
    }


# ----------------------------------------------------------------------
# Tracker-hit analysis
# ----------------------------------------------------------------------

def analyse_tracker_hits(event, chargino_trackid, decoders):
    """
    Select ONLY tracker hits whose stored Geant4 track ID corresponds
    to the chargino.

    In SimG4SaveTrackerHits:
        SimTrackerHit.quality = Geant4 track ID

    In SimParticleSecondaries:
        MCParticle.simulatorStatus = Geant4 track ID
    """

    chargino_hits = []
    layers = set()

    for collection_name in [
        "TrackerBarrelReadout",
        "TrackerEndcapReadout",
    ]:

        hits = event.get(collection_name)

        decoder = decoders[collection_name]

        for hit in hits:

            trackid = int(hit.getQuality())

            if trackid != chargino_trackid:
                continue

            pos = hit.getPosition()

            r = math.sqrt(
                pos.x * pos.x +
                pos.y * pos.y
            )

            decoded = decode_hit(
                hit.getCellID(),
                collection_name,
                decoder,
            )

            layers.add(decoded["layer_key"])

            chargino_hits.append({
                "collection": collection_name,
                "x": pos.x,
                "y": pos.y,
                "z": pos.z,
                "r": r,
                **decoded,
            })

    return chargino_hits, layers


# ----------------------------------------------------------------------
# Event loop
# ----------------------------------------------------------------------

def analyse_file(filename):

    _, decoders = setup_geometry()

    reader = root_io.Reader(filename)

    rows = []

    for iev, event in enumerate(reader.get("events")):

        particles = event.get("SimParticleSecondaries")

        chargino = find_chargino(particles)

        if chargino is None:
            print(
                f"WARNING event {iev}: "
                "could not identify unique chargino"
            )
            continue

        trackid = int(chargino.getSimulatorStatus())

        decay = find_decay_vertex(
            particles,
            chargino,
        )

        if decay is None:
            print(
                f"WARNING event {iev}: "
                "could not identify chargino decay vertex"
            )
            continue

        hits, layers = analyse_tracker_hits(
            event,
            trackid,
            decoders,
        )

        # Split layer counts by detector region
        barrel_layers = {
            h["layer_key"]
            for h in hits
            if h["region"] == "barrel"
        }

        endcap_layers = {
            h["layer_key"]
            for h in hits
            if h["region"] == "endcap"
        }

        hit_radii = [h["r"] for h in hits]

        row = {
            "event": iev,

            "chargino_pdg": chargino.getPDG(),
            "chargino_trackid": trackid,

            "chargino_p": momentum_magnitude(chargino),
            "chargino_pt": particle_pt(chargino),
            "chargino_eta": particle_eta(chargino),

            "decay_x": decay["x"],
            "decay_y": decay["y"],
            "decay_z": decay["z"],
            "decay_r": decay["r"],

            "pion_trackid": decay["pion_trackid"],
            "neutralino_trackid": decay["neutralino_trackid"],

            "n_chargino_hits": len(hits),
            "n_chargino_layers": len(layers),

            "n_barrel_layers": len(barrel_layers),
            "n_endcap_layers": len(endcap_layers),

            "first_hit_r": (
                min(hit_radii)
                if hit_radii else np.nan
            ),

            "last_hit_r": (
                max(hit_radii)
                if hit_radii else np.nan
            ),

            "layer_keys": ",".join(sorted(layers)),
        }

        rows.append(row)

    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Plots
# ----------------------------------------------------------------------

def plot_layers_vs_decay_radius(df, output_prefix):

    plt.figure(figsize=(8, 6))

    plt.scatter(
        df["decay_r"],
        df["n_chargino_layers"],
        s=20,
        alpha=0.7,
    )

    plt.xlabel(r"Chargino decay radius $r_{\rm decay}$ [mm]")
    plt.ylabel("Number of tracker layers with chargino hits")

    plt.tight_layout()

    plt.savefig(
        f"{output_prefix}_layers_vs_decay_radius.pdf"
    )

    plt.savefig(
        f"{output_prefix}_layers_vs_decay_radius.png",
        dpi=200,
    )

    plt.close()


def calculate_efficiency(
    df,
    minimum_layers,
    bins,
):

    decay_r = df["decay_r"].to_numpy()
    passed = (
        df["n_chargino_layers"].to_numpy()
        >= minimum_layers
    )

    centres = 0.5 * (bins[:-1] + bins[1:])

    efficiency = np.full(
        len(centres),
        np.nan,
    )

    uncertainty = np.full(
        len(centres),
        np.nan,
    )

    n_total = np.zeros(
        len(centres),
        dtype=int,
    )

    n_pass = np.zeros(
        len(centres),
        dtype=int,
    )

    for i in range(len(bins) - 1):

        mask = (
            (decay_r >= bins[i]) &
            (decay_r < bins[i + 1])
        )

        n = np.sum(mask)
        k = np.sum(passed[mask])

        n_total[i] = n
        n_pass[i] = k

        if n > 0:

            eff = k / n

            efficiency[i] = eff

            # Simple binomial uncertainty.
            uncertainty[i] = math.sqrt(
                eff * (1.0 - eff) / n
            )

    return (
        centres,
        efficiency,
        uncertainty,
        n_pass,
        n_total,
    )


def plot_efficiencies(df, output_prefix):

    if len(df) == 0:
        return

    max_r = df["decay_r"].max()

    # Start with 25 mm bins.
    # Easy to change once we have higher statistics.
    upper = max(
        100.0,
        math.ceil(max_r / 25.0) * 25.0,
    )

    bins = np.arange(
        0.0,
        upper + 25.0,
        25.0,
    )

    plt.figure(figsize=(8, 6))

    efficiency_tables = []

    for minimum_layers in [1, 2, 3, 4, 5, 6]:

        (
            centres,
            efficiency,
            uncertainty,
            n_pass,
            n_total,
        ) = calculate_efficiency(
            df,
            minimum_layers,
            bins,
        )

        valid = ~np.isnan(efficiency)

        plt.errorbar(
            centres[valid],
            efficiency[valid],
            yerr=uncertainty[valid],
            marker="o",
            linestyle="-",
            label=rf"$N_{{layers}}\geq {minimum_layers}$",
        )

        for centre, eff, err, passed, total in zip(
            centres,
            efficiency,
            uncertainty,
            n_pass,
            n_total,
        ):

            efficiency_tables.append({
                "minimum_layers": minimum_layers,
                "decay_r_centre": centre,
                "decay_r_low": centre - 12.5,
                "decay_r_high": centre + 12.5,
                "efficiency": eff,
                "uncertainty": err,
                "n_pass": passed,
                "n_total": total,
            })

    plt.xlabel(
        r"Chargino decay radius $r_{\rm decay}$ [mm]"
    )

    plt.ylabel(
        "Chargino tracker-layer efficiency"
    )

    plt.ylim(-0.05, 1.05)

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        f"{output_prefix}_efficiency_vs_decay_radius.pdf"
    )

    plt.savefig(
        f"{output_prefix}_efficiency_vs_decay_radius.png",
        dpi=200,
    )

    plt.close()

    pd.DataFrame(
        efficiency_tables
    ).to_csv(
        f"{output_prefix}_efficiency.csv",
        index=False,
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        help="FCCSW EDM4hep simulation ROOT file",
    )

    parser.add_argument(
        "--output",
        default="chargino_efficiency",
        help="Output file prefix",
    )

    args = parser.parse_args()

    print(f"Reading {args.input}")

    df = analyse_file(args.input)

    print()
    print("========================================")
    print("Summary")
    print("========================================")
    print(f"Events analysed:       {len(df)}")

    if len(df):

        print(
            "Events with >=1 chargino hit: "
            f"{np.sum(df['n_chargino_hits'] > 0)}"
        )

        print(
            "Events with >=1 layer:        "
            f"{np.sum(df['n_chargino_layers'] > 0)}"
        )

        print(
            "Mean decay radius [mm]:       "
            f"{df['decay_r'].mean():.3f}"
        )

        print(
            "Maximum decay radius [mm]:    "
            f"{df['decay_r'].max():.3f}"
        )

    csv_name = f"{args.output}_events.csv"

    df.to_csv(
        csv_name,
        index=False,
    )

    print()
    print(f"Wrote {csv_name}")

    if len(df):

        plot_layers_vs_decay_radius(
            df,
            args.output,
        )

        plot_efficiencies(
            df,
            args.output,
        )

        print(
            f"Wrote {args.output}_layers_vs_decay_radius.pdf"
        )

        print(
            f"Wrote {args.output}_efficiency_vs_decay_radius.pdf"
        )

        print(
            f"Wrote {args.output}_efficiency.csv"
        )


if __name__ == "__main__":
    main()