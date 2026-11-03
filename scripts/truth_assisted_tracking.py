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
              'n_hits', 'fit_status', 'fitted_radius_mm', 'fitted_pt_gev',
              'fitted_p_gev', 'slope_dz_ds', 'chi2', 'ndof', 'chi2_ndof',
              'first_hit_r_mm', 'last_hit_r_mm']
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
            row['n_hits'] = len(hits)
            if len(hits) < args.min_hits:
                row['fit_status'] = 'too_few_hits'
            else:
                try:
                    row.update(fit_helix(np.array(hits), args.bz_tesla,
                                         args.sigma_rphi_mm, args.sigma_z_mm))
                    row['fit_status'] = 'ok'
                except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                    row['fit_status'] = 'fit_failed'
                    print(f'Event {i}: fit failed: {exc}')
            writer.writerow(row)
            counts[row['fit_status']] = counts.get(row['fit_status'], 0)+1
    print(f'Wrote {output}')
    print('Status counts:', counts)
    print('NOTE: circle/line fit assumes uniform Bz and is not a full tracking reconstruction.')


if __name__ == '__main__':
    main()
