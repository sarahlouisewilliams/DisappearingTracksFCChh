#!/usr/bin/env python3
"""Two checks for the FCC-hh Stage 2 decaying-chargino truth-assisted fit.

1. Number of associated tracker hits vs transverse decay radius (including zero hits).
2. Median and 16th/84th percentiles of relative pT residual vs radius and hit count.

The input is the event-level CSV written by truth_assisted_tracking_decays.py.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def summarise(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return None
    q16, med, q84 = np.percentile(a, [16, 50, 84])
    return dict(n=int(len(a)), median=float(med), p16=float(q16), p84=float(q84))


def save_plot(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    print('Saved', path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('csv', help='Output of truth_assisted_tracking_decays.py')
    ap.add_argument('--output-prefix', default='results/decay_tau5ns_checks')
    ap.add_argument('--min-hits', type=int, default=4)
    ap.add_argument('--min-bin-count', type=int, default=20,
                    help='Minimum successful fits to show a residual summary point')
    ap.add_argument('--radius-bins', type=float, nargs='+',
                    default=[0, 100, 150, 200, 300, 400, 600, 800, 1000,
                             1250, 1500, 2000, 3000, 5000],
                    help='Transverse decay-radius bin edges in mm')
    args = ap.parse_args()
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    bins = np.asarray(args.radius_bins, dtype=float)
    if len(bins) < 2 or not np.all(np.diff(bins) > 0):
        ap.error('--radius-bins must be strictly increasing')

    df = pd.read_csv(args.csv)
    required = {'decay_status', 'decay_r_mm', 'n_hits', 'fit_status',
                'fitted_pt_gev', 'truth_pt_gev'}
    missing = required.difference(df.columns)
    if missing:
        ap.error('Missing CSV columns: ' + ', '.join(sorted(missing)))

    # The current Stage 2 writer outputs one row per event with a unique chargino,
    # including zero-hit events. A matched decay vertex is required to bin in r.
    df['decay_r_mm'] = pd.to_numeric(df.decay_r_mm, errors='coerce')
    df['n_hits'] = pd.to_numeric(df.n_hits, errors='coerce')
    matched = df[(df.decay_status == 'ok') & np.isfinite(df.decay_r_mm)
                 & (df.decay_r_mm >= 0) & np.isfinite(df.n_hits)].copy()
    print(f'CSV rows: {len(df)}; matched decay radius: {len(matched)}; '
          f'excluded: {len(df) - len(matched)}')
    if matched.empty:
        raise SystemExit('No matched decay vertices; inspect decay_status and history matching.')

    matched['enough_hits'] = matched.n_hits >= args.min_hits
    matched['fit_ok'] = matched.fit_status.eq('ok')
    matched['r_bin'] = pd.cut(matched.decay_r_mm, bins=bins, right=False,
                              include_lowest=True)
    in_range = matched[matched.r_bin.notna()].copy()
    print(f'Matched decays inside radius bins: {len(in_range)}; '
          f'outside: {len(matched) - len(in_range)}')

    # Check 1a: all hit multiplicities (zero-hit tracks included) versus radius.
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(in_range.decay_r_mm, in_range.n_hits, s=6, alpha=0.18,
               rasterized=True)
    ax.axhline(args.min_hits, ls='--', color='black', lw=1.2,
               label=f'Minimum for fit: {args.min_hits} hits')
    ax.set(xlabel='Transverse decay radius [mm]',
           ylabel='Number of chargino-associated tracker hits',
           title='Hit multiplicity versus decay radius')
    ax.legend()
    ax.grid(alpha=0.25)
    save_plot(fig, str(prefix) + '_hits_vs_radius.png')

    # Check 1b: occupancy and fit fractions in each radius bin.
    occupancy = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        s = in_range[(in_range.decay_r_mm >= lo) & (in_range.decay_r_mm < hi)]
        if len(s) == 0:
            continue
        occupancy.append(dict(r_lo_mm=lo, r_hi_mm=hi, n_decays=len(s),
                              n_zero_hits=int((s.n_hits == 0).sum()),
                              mean_hits=float(s.n_hits.mean()),
                              median_hits=float(s.n_hits.median()),
                              fraction_enough_hits=float(s.enough_hits.mean()),
                              fraction_fit_ok=float(s.fit_ok.mean())))
    occ = pd.DataFrame(occupancy)
    occ.to_csv(str(prefix) + '_hit_occupancy.csv', index=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    x = (occ.r_lo_mm + occ.r_hi_mm) / 2
    xerr = (occ.r_hi_mm - occ.r_lo_mm) / 2
    ax.errorbar(x, occ.fraction_enough_hits, xerr=xerr, fmt='o-',
                capsize=2, label=f'At least {args.min_hits} hits')
    ax.errorbar(x, occ.fraction_fit_ok, xerr=xerr, fmt='s--',
                capsize=2, label='Successful helix fit')
    ax.set(xlabel='Transverse decay radius [mm]', ylabel='Fraction of matched decays',
           ylim=(-0.05, 1.05), title='Hit threshold and fit success versus decay radius')
    ax.legend()
    ax.grid(alpha=0.25)
    save_plot(fig, str(prefix) + '_hit_threshold_vs_radius.png')

    # Check 2: only successful fits with finite truth and fitted pT.
    fit = in_range[in_range.fit_ok].copy()
    fit['fitted_pt_gev'] = pd.to_numeric(fit.fitted_pt_gev, errors='coerce')
    fit['truth_pt_gev'] = pd.to_numeric(fit.truth_pt_gev, errors='coerce')
    fit = fit[np.isfinite(fit.fitted_pt_gev) & np.isfinite(fit.truth_pt_gev)
              & (fit.truth_pt_gev > 0)].copy()
    fit['residual_pct'] = 100.0 * (fit.fitted_pt_gev - fit.truth_pt_gev) / fit.truth_pt_gev
    fit = fit[np.isfinite(fit.residual_pct)].copy()

    radius_rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        s = fit[(fit.decay_r_mm >= lo) & (fit.decay_r_mm < hi)]
        stats = summarise(s.residual_pct)
        if stats is not None:
            radius_rows.append(dict(r_lo_mm=lo, r_hi_mm=hi, **stats))
    radius_summary = pd.DataFrame(radius_rows, columns=['r_lo_mm', 'r_hi_mm', 'n',
                                                        'median', 'p16', 'p84'])
    radius_summary.to_csv(str(prefix) + '_residual_vs_radius.csv', index=False)

    hit_rows = []
    for nhits, s in fit.groupby('n_hits'):
        stats = summarise(s.residual_pct)
        if stats is not None:
            hit_rows.append(dict(n_hits=int(nhits), **stats))
    hit_summary = pd.DataFrame(hit_rows, columns=['n_hits', 'n', 'median', 'p16', 'p84'])
    hit_summary.to_csv(str(prefix) + '_residual_vs_hits.csv', index=False)

    for name, summary, xkey in [('radius', radius_summary, 'radius'),
                                 ('hits', hit_summary, 'hits')]:
        fig, ax = plt.subplots(figsize=(9, 5))
        shown = summary[summary.n >= args.min_bin_count].copy()
        if not shown.empty:
            if xkey == 'radius':
                xpos = (shown.r_lo_mm + shown.r_hi_mm) / 2
                errx = (shown.r_hi_mm - shown.r_lo_mm) / 2
            else:
                xpos, errx = shown.n_hits, None
            yerr = np.vstack([shown['median'] - shown.p16,
                              shown.p84 - shown['median']])
            ax.errorbar(xpos, shown['median'], xerr=errx, yerr=yerr,
                        fmt='o-', capsize=3, label='Median and 16th–84th percentiles')
            # Mark count per displayed bin, making sparse regions obvious.
            for xx, yy, nn in zip(xpos, shown['median'], shown.n):
                ax.annotate(f'n={nn}', (xx, yy), xytext=(0, 8),
                            textcoords='offset points', ha='center', fontsize=7)
        ax.axhline(0, color='gray', lw=1)
        ax.set(xlabel='Transverse decay radius [mm]' if xkey == 'radius'
               else 'Number of chargino-associated tracker hits',
               ylabel='(fitted pT − truth pT) / truth pT [%]',
               title=f'Momentum residual versus {"decay radius" if xkey == "radius" else "hit count"}')
        ax.grid(alpha=0.25)
        if not shown.empty:
            ax.legend()
        save_plot(fig, str(prefix) + f'_residual_summary_vs_{name}.png')

    print('\nHit occupancy by decay radius:')
    print(occ.to_string(index=False))
    print('\nMomentum residual vs radius (%):')
    print(radius_summary.to_string(index=False))
    print('\nMomentum residual vs hit count (%):')
    print(hit_summary.to_string(index=False))
    print(f'\nSuccessful fits with finite residuals inside bins: {len(fit)}')
    print('Note: all efficiency denominators are conditional on matched decay vertices.')


if __name__ == '__main__':
    main()
