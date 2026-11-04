#!/usr/bin/env python3
"""Prototype truth-assisted helical fits to FCC-hh Geant4 SimTrackerHits.

This is a stand-alone *diagnostic*, not digitisation, GenFit or EDM4hep Track
reconstruction. Uses hit positions, truth association and a uniform Bz model.
"""
import argparse
import csv
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from podio import root_io


def vec3(v):
    return np.array([v.x, v.y, v.z], dtype=float)


def select_chargino(event):
    ps = event.get('SimParticleSecondaries')
    found = [p for p in ps if abs(p.getPDG()) == 1000024]
    return found[0] if len(found) == 1 else None


def find_decay_vertex(event, chargino):
    """Infer decay vertex from neutralino and same-sign pion production vertices.

    Particle-history parent/daughter relations are not assumed to be populated.
    Ambiguous or absent candidates return NaN, never a fabricated decay radius.
    """
    particles = event.get('SimParticleSecondaries')
    neutralinos = [p for p in particles if abs(p.getPDG()) == 1000022]
    pion_pdg = 211 if chargino.getPDG() > 0 else -211
    pions = [p for p in particles if p.getPDG() == pion_pdg]
    if len(neutralinos) != 1 or len(pions) != 1:
        return math.nan, math.nan, 'missing_or_ambiguous_daughters'
    v0 = vec3(neutralinos[0].getVertex())
    v1 = vec3(pions[0].getVertex())
    if not np.all(np.isfinite(v0)) or not np.all(np.isfinite(v1)):
        return math.nan, math.nan, 'invalid_vertex'
    if np.linalg.norm(v0-v1) > 0.1:  # mm; check consistency of shared production vertex
        return math.nan, math.nan, 'daughter_vertex_mismatch'
    return float(np.linalg.norm(v0[:2])), float(np.linalg.norm(v0)), 'ok'


def circle_fit(xy):
    # Algebraic seed, then geometric least squares.
    x, y = xy[:, 0], xy[:, 1]
    a = np.column_stack((2*x, 2*y, np.ones(len(x))))
    cx, cy, k = np.linalg.lstsq(a, x*x + y*y, rcond=None)[0]
    radius = math.sqrt(max(k + cx*cx + cy*cy, 0))
    fit = least_squares(lambda p: np.hypot(x-p[0], y-p[1])-p[2],
                        [cx, cy, radius], bounds=([-np.inf, -np.inf, 0],
                                                   [np.inf, np.inf, np.inf]))
    return fit.x, fit.fun


def sagitta_diagnostic(positions_mm, truth_pt_gev, bz_t):
    """Independent transverse chord/sagitta check, without a circle fit.

    Assumes outward-going, non-looping tracks. The signed sagitta is the
    perpendicular distance at the hit nearest the transverse chord midpoint;
    max_abs_sagitta_mm uses all intermediate hits and is less directly
    comparable with the ideal midpoint prediction.
    """
    hits = positions_mm[np.argsort(np.linalg.norm(positions_mm[:, :2], axis=1))]
    xy = hits[:, :2]
    chord = xy[-1] - xy[0]
    length = float(np.linalg.norm(chord))
    if length <= 0 or len(xy) < 3:
        raise ValueError("Need at least 3 distinct transverse hit positions")
    unit = chord / length
    relative = xy - xy[0]
    projection = relative @ unit
    signed = unit[0] * relative[:, 1] - unit[1] * relative[:, 0]
    # Choose the interior hit nearest the halfway point of the chord.
    mid_idx = 1 + int(np.argmin(np.abs(projection[1:-1] - length / 2)))
    # Expected midpoint sagitta for uniform B and a circular arc; small-angle.
    expected = (length * length * 0.000299792458 * abs(bz_t)
                / (8.0 * truth_pt_gev)) if truth_pt_gev > 0 else math.nan
    return dict(chord_length_mm=length,
                sagitta_mid_mm=float(signed[mid_idx]),
                sagitta_mid_fraction=float(projection[mid_idx] / length),
                max_abs_sagitta_mm=float(np.max(np.abs(signed[1:-1]))),
                expected_sagitta_mm=expected)


def fit_helix(positions_mm, bz_t, sigma_rphi_mm, sigma_z_mm):
    # Sort by radial distance: valid for outward-going, non-looping trajectories.
    hits = positions_mm[np.argsort(np.linalg.norm(positions_mm[:, :2], axis=1))]
    (cx, cy, radius), radial_resid = circle_fit(hits[:, :2])
    angles = np.unwrap(np.arctan2(hits[:, 1]-cy, hits[:, 0]-cx))
    arc = radius * (angles - angles[0])
    # z = z0 + slope * signed transverse arc length.
    slope, intercept = np.polyfit(arc, hits[:, 2], 1)
    zres = hits[:, 2] - (slope*arc + intercept)
    chi2 = np.sum((radial_resid/sigma_rphi_mm)**2) + np.sum((zres/sigma_z_mm)**2)
    ndof = 3*len(hits) - 5  # approximate: 3D point model with five fitted parameters
    pt_gev = 0.000299792458 * abs(bz_t) * radius
    p_gev = pt_gev * math.sqrt(1+slope*slope)
    return dict(n_hits=len(hits), fitted_radius_mm=radius, fitted_pt_gev=pt_gev,
                fitted_p_gev=p_gev, slope_dz_ds=slope, chi2=chi2, ndof=ndof,
                chi2_ndof=chi2/ndof if ndof > 0 else math.nan,
                first_hit_r_mm=np.linalg.norm(hits[0, :2]),
                last_hit_r_mm=np.linalg.norm(hits[-1, :2]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', help='Simulation EDM4hep ROOT file')
    ap.add_argument('--output', default='tracking_truth_fit.csv', help='Output CSV')
    ap.add_argument('--bz-tesla', type=float, required=True,
                    help='Approximate uniform solenoidal Bz; verify against FCC-hh field map')
    ap.add_argument('--min-hits', type=int, default=4)
    ap.add_argument('--sigma-rphi-mm', type=float, default=0.01,
                    help='Effective transverse hit resolution, NOT detector digitisation')
    ap.add_argument('--sigma-z-mm', type=float, default=0.05,
                    help='Effective longitudinal hit resolution, NOT detector digitisation')
    args = ap.parse_args()
    if args.bz_tesla == 0 or args.min_hits < 3 or args.sigma_rphi_mm <= 0 or args.sigma_z_mm <= 0:
        ap.error('Require nonzero Bz, min-hits >= 3, and positive resolutions')

    fields = ['event', 'chargino_g4_id', 'pdg', 'truth_pt_gev', 'truth_p_gev',
              'decay_r_mm', 'decay_distance_mm', 'decay_status',
              'n_hits', 'fit_status', 'fitted_radius_mm', 'fitted_pt_gev',
              'fitted_p_gev', 'slope_dz_ds', 'chi2', 'ndof', 'chi2_ndof',
              'first_hit_r_mm', 'last_hit_r_mm',
              'chord_length_mm', 'sagitta_mid_mm', 'sagitta_mid_fraction',
              'max_abs_sagitta_mm', 'expected_sagitta_mm']
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    with output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        reader = root_io.Reader(args.input)
        for i, event in enumerate(reader.get('events')):
            p = select_chargino(event)
            if p is None:
                counts['missing_or_multiple_charginos'] = counts.get('missing_or_multiple_charginos', 0)+1
                continue
            mom = vec3(p.getMomentum())
            g4id = p.getSimulatorStatus()
            row = dict(event=i, chargino_g4_id=g4id, pdg=p.getPDG(),
                       truth_pt_gev=np.linalg.norm(mom[:2]), truth_p_gev=np.linalg.norm(mom))
            hits = []
            for name in ('TrackerBarrelReadout', 'TrackerEndcapReadout'):
                for h in event.get(name):
                    if h.getQuality() == g4id:
                        hits.append(vec3(h.getPosition()))
            decay_r, decay_dist, decay_status = find_decay_vertex(event, p)
            row.update(decay_r_mm=decay_r, decay_distance_mm=decay_dist,
                       decay_status=decay_status)
            row['n_hits'] = len(hits)
            if hits:
                radii = [float(np.linalg.norm(h[:2])) for h in hits]
                row['first_hit_r_mm'] = min(radii)
                row['last_hit_r_mm'] = max(radii)
            if len(hits) < args.min_hits:
                row['fit_status'] = 'too_few_hits'
            else:
                try:
                    positions = np.array(hits)
                    row.update(sagitta_diagnostic(positions, row['truth_pt_gev'],
                                                  args.bz_tesla))
                    row.update(fit_helix(positions, args.bz_tesla,
                                         args.sigma_rphi_mm, args.sigma_z_mm))
                    row['fit_status'] = 'ok'
                except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                    row['fit_status'] = 'fit_failed'
                    print(f'Event {i}: fit failed: {exc}')
            writer.writerow(row)
            counts[row['fit_status']] = counts.get(row['fit_status'], 0)+1
    print(f'Wrote {output}')
    print('Status counts:', counts)
    print('NOTE: one CSV row per event with a unique chargino, including zero-hit events.')
    print('NOTE: circle/line fit assumes uniform Bz and is not a full tracking reconstruction.')


if __name__ == '__main__':
    main()
