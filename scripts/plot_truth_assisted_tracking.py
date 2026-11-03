#!/usr/bin/env python3
"""Plot diagnostic performance from truth_assisted_tracking.py CSV."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', help='CSV from truth_assisted_tracking.py')
    ap.add_argument('--output', default='tracking', help='Output filename prefix')
    args = ap.parse_args()
    df = pd.read_csv(args.input)
    prefix = Path(args.output)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    ok = df[df.fit_status == 'ok'].copy()
    if len(ok) == 0:
        raise SystemExit('No successful fits in input CSV')
    ok = ok[np.isfinite(ok.fitted_pt_gev) & (ok.truth_pt_gev > 0)]
    ok['pt_residual'] = (ok.fitted_pt_gev - ok.truth_pt_gev) / ok.truth_pt_gev
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(ok.n_hits, ok.pt_residual, s=12, alpha=0.5)
    ax.axhline(0, color='gray', lw=1)
    ax.set(xlabel='Number of truth-associated SimTrackerHits',
           ylabel=r'$(p_{T,\mathrm{fit}}-p_{T,\mathrm{truth}})/p_{T,\mathrm{truth}}$',
           title='Diagnostic circle-fit momentum residual')
    fig.tight_layout()
    fig.savefig(str(prefix) + '_pt_residual_vs_hits.png', dpi=160)
    fig.savefig(str(prefix) + '_pt_residual_vs_hits.pdf')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(ok.chi2_ndof.dropna(), bins=50)
    ax.set(xlabel='Approximate fit chi2/ndof', ylabel='Events',
           title='Diagnostic fit quality (not calibrated)')
    fig.tight_layout()
    fig.savefig(str(prefix) + '_chi2_ndof.png', dpi=160)
    fig.savefig(str(prefix) + '_chi2_ndof.pdf')
    plt.close(fig)
    print(f'Plotted {len(ok)} fitted events with prefix {prefix}')


if __name__ == '__main__':
    main()
