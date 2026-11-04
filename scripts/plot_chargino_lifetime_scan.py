#!/usr/bin/env python3
"""Summarise lifetime scan from truth_assisted_tracking_decays.py CSV files.

CSV rows represent events with exactly one selected chargino; use --generated
for the total generated-event denominator and report unmatched events separately.
"""
import argparse
from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TAUS = [0.2, 1.0, 2.0, 5.0, 10.0]

def wilson(k, n, z=1.0):
    if n <= 0:
        return (np.nan, np.nan)
    p = k/n
    d = 1 + z*z/n
    mid = (p + z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (mid-half, mid+half)

def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    print('Saved', path)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--directory', default='results/lifetime_scan')
    ap.add_argument('--generated', type=int, default=10000,
                    help='Number of generated events PER lifetime (must match each run)')
    ap.add_argument('--output-prefix', default='results/lifetime_scan/lifetime_scan')
    ap.add_argument('--thresholds', type=int, nargs='+', default=[4,5,6,7,8])
    ap.add_argument('--min-fit-count', type=int, default=20)
    args = ap.parse_args()
    if args.generated <= 0: ap.error('--generated must be positive')
    out = Path(args.output_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, resolutions = [], []
    for tau in TAUS:
        tag = f'tau{str(tau).replace(".", "p")}ns'
        print("tag: ", str(tag))
        file = Path(args.directory) / f'chargino_{tag}_fit.csv'
        print("file: ", str(file))
        if not file.exists():
            raise FileNotFoundError(f'Missing {file}; run the simulation/fit first')
        df = pd.read_csv(file)
        required = {'n_hits','fit_status','truth_pt_gev','fitted_pt_gev','decay_r_mm','decay_status'}
        missing = required - set(df.columns)
        if missing: raise ValueError(f'{file} missing columns: {sorted(missing)}')
        if len(df) > args.generated:
            raise ValueError(f'{file} has {len(df)} rows, more than --generated={args.generated}')
        nh = pd.to_numeric(df['n_hits'], errors='coerce').fillna(-1)
        ok = df['fit_status'].eq('ok')
        matched = pd.to_numeric(df['decay_r_mm'], errors='coerce').notna()
        row = {'lifetime_ns':tau,'n_generated':args.generated,
               'n_selected_charginos':len(df),
               'n_missing_or_ambiguous_charginos':args.generated-len(df),
               'n_decay_vertices_matched':int(matched.sum()),
               'n_successful_fits':int(ok.sum()),
               'fit_efficiency_generated':ok.sum()/args.generated}
        for threshold in args.thresholds:
            k = int((nh>=threshold).sum())
            lo,hi = wilson(k,args.generated)
            row[f'n_hits_ge_{threshold}']=k
            row[f'eff_hits_ge_{threshold}']=k/args.generated
            row[f'eff_hits_ge_{threshold}_low68']=lo
            row[f'eff_hits_ge_{threshold}_high68']=hi
        rows.append(row)
        # Conditional momentum performance among successful fits only.
        truth = pd.to_numeric(df['truth_pt_gev'],errors='coerce')
        fit = pd.to_numeric(df['fitted_pt_gev'],errors='coerce')
        residual = 100*(fit-truth)/truth
        good = ok & np.isfinite(residual) & (truth>0)
        vals = residual[good].to_numpy()
        if len(vals)>=args.min_fit_count:
            p16,med,p84 = np.percentile(vals,[16,50,84])
        else:
            p16=med=p84=np.nan
        resolutions.append({'lifetime_ns':tau,'n_good_fits':len(vals),
                            'median_residual_pct':med,'p16_pct':p16,'p84_pct':p84})
        print(f'tau={tau:g} ns: selected={len(df)}/{args.generated}, '
              f'decay vertices={matched.sum()}, fit={ok.sum()}')
    tab=pd.DataFrame(rows)
    tab.to_csv(str(out)+'_efficiencies.csv',index=False)
    perf=pd.DataFrame(resolutions)
    perf.to_csv(str(out)+'_momentum_summary.csv',index=False)
    x=tab['lifetime_ns'].to_numpy()
    fig,ax=plt.subplots(figsize=(8,5))
    for threshold in args.thresholds:
        y=tab[f'eff_hits_ge_{threshold}'].to_numpy()
        low=tab[f'eff_hits_ge_{threshold}_low68'].to_numpy()
        high=tab[f'eff_hits_ge_{threshold}_high68'].to_numpy()
        ax.errorbar(x,y,yerr=[y-low,high-y],marker='o',capsize=2,label=f'≥{threshold} hits')
    ax.set(xlabel='Chargino proper lifetime [ns]',ylabel='Fraction of generated events',ylim=(0,1.05),
           title='Truth-associated hit acceptance versus lifetime')
    ax.set_xscale('log'); ax.grid(alpha=.25); ax.legend()
    save(fig,str(out)+'_hit_acceptance.png')
    fig,ax=plt.subplots(figsize=(8,5))
    y=tab['fit_efficiency_generated'].to_numpy()
    lo,hi=np.array([wilson(int(k),args.generated) for k in tab['n_successful_fits']]).T
    ax.errorbar(x,y,yerr=[y-lo,hi-y],marker='o',capsize=3)
    ax.set(xlabel='Chargino proper lifetime [ns]',ylabel='Successful fits / generated events',ylim=(0,1.05),
           title='Truth-assisted fit efficiency versus lifetime')
    ax.set_xscale('log'); ax.grid(alpha=.25)
    save(fig,str(out)+'_fit_efficiency.png')
    fig,ax=plt.subplots(figsize=(8,5))
    p=perf.dropna(subset=['median_residual_pct'])
    if len(p):
        med=p['median_residual_pct'].to_numpy()
        low=p['p16_pct'].to_numpy()
        high=p['p84_pct'].to_numpy()
        ax.errorbar(p['lifetime_ns'],med,yerr=[med-low,high-med],fmt='o-',capsize=3)
    ax.axhline(0,color='gray',linewidth=1)
    ax.set(xlabel='Chargino proper lifetime [ns]',ylabel='Relative pT residual [%]',
           title='Conditional momentum performance of successful fits')
    ax.set_xscale('log'); ax.grid(alpha=.25)
    save(fig,str(out)+'_momentum_performance.png')
    print('\n'+tab[['lifetime_ns','n_selected_charginos','n_decay_vertices_matched',
                         'n_successful_fits','fit_efficiency_generated']].to_string(index=False))
    if any(tab['n_missing_or_ambiguous_charginos']):
        print('WARNING: Some generated events had no unique selected chargino. '
              'These count as failures in generated-event efficiencies; investigate if numerous.')
    print('NOTE: ≥N hit curves are geometric/truth-associated acceptance, not fit efficiency for N>4.')
    print('NOTE: Error bars on efficiencies are approximate 68% Wilson intervals; '
          'momentum bars are 16th–84th percentile widths, NOT uncertainty on median.')

if __name__=='__main__':
    main()
