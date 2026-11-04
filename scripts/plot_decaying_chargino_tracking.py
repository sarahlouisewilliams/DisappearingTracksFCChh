#!/usr/bin/env python3
"""Plot truth-assisted fit efficiency and pT residual vs decay radius and hits.
Denominator: all rows with a unique chargino and a matched decay vertex.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('csv')
ap.add_argument('--output-prefix', default='results/decaying_chargino')
ap.add_argument('--min-denominator', type=int, default=10)
a = ap.parse_args()
df = pd.read_csv(a.csv)
df = df[(df.decay_status == 'ok') & np.isfinite(df.decay_r_mm)].copy()
if df.empty:
    raise SystemExit('No matched decay vertices. Check daughter PDG/vertex matching and history output.')
df['fit_ok'] = df.fit_status.eq('ok')
df['residual'] = (df.fitted_pt_gev - df.truth_pt_gev) / df.truth_pt_gev
prefix = Path(a.output_prefix)
prefix.parent.mkdir(parents=True, exist_ok=True)

# Binned conditional fit efficiency vs transverse decay radius.
bins = np.array([0, 25, 60, 102, 150, 264, 395, 529, 751, 931, 1136, 1320, 1520, 2000, 3000], float)
rows=[]
for lo,hi in zip(bins[:-1],bins[1:]):
    sample=df[(df.decay_r_mm >= lo) & (df.decay_r_mm < hi)]
    n=len(sample)
    if n:
        rows.append(dict(r_lo_mm=lo,r_hi_mm=hi,n_generated=n,n_fit=int(sample.fit_ok.sum()),efficiency=float(sample.fit_ok.mean())))
summary=pd.DataFrame(rows)
summary.to_csv(str(prefix)+'_efficiency.csv',index=False)
fig,ax=plt.subplots(figsize=(8,4.5))
sel=summary[summary.n_generated>=a.min_denominator]
if not sel.empty:
    x=(sel.r_lo_mm+sel.r_hi_mm)/2
    ax.errorbar(x,sel.efficiency,xerr=(sel.r_hi_mm-sel.r_lo_mm)/2,fmt='o',capsize=2)
ax.set(xlabel='Transverse decay radius [mm]',ylabel='Truth-assisted fit efficiency',ylim=(-0.05,1.05))
ax.grid(alpha=.25)
fig.tight_layout();fig.savefig(str(prefix)+'_efficiency.png',dpi=180);plt.close(fig)

fitted=df[df.fit_ok & np.isfinite(df.residual)].copy()
fig,ax=plt.subplots(figsize=(8,4.5))
if not fitted.empty:
    ax.scatter(fitted.decay_r_mm, fitted.residual, s=8,alpha=.4)
ax.axhline(0,color='gray',lw=1)
ax.set(xlabel='Transverse decay radius [mm]',ylabel='(fitted pT - truth pT) / truth pT')
ax.grid(alpha=.25)
fig.tight_layout();fig.savefig(str(prefix)+'_pt_residual_vs_radius.png',dpi=180);plt.close(fig)

fig,ax=plt.subplots(figsize=(8,4.5))
if not fitted.empty:
    ax.scatter(fitted.n_hits, fitted.residual, s=8,alpha=.4)
ax.axhline(0,color='gray',lw=1)
ax.set(xlabel='Number of chargino-associated tracker hits',ylabel='(fitted pT - truth pT) / truth pT')
ax.grid(alpha=.25)
fig.tight_layout();fig.savefig(str(prefix)+'_pt_residual_vs_hits.png',dpi=180);plt.close(fig)
print('Matched decays:',len(df),'Fitted:',len(fitted),'Conditional fit fraction:',len(fitted)/len(df))
print('Hit multiplicities:\n',df.n_hits.value_counts().sort_index().to_string())
print('Efficiency bins:\n',summary.to_string(index=False))
print('Outputs:',prefix)
