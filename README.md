# FCC-hh disappearing-chargino simulation tutorial

This tutorial generates individual charginos, simulates their decays in the FCC-hh detector with Geant4, persists particle history and tracker hits, and studies **truth-level** layer acceptance. **Track reconstruction is not yet included.**

The descriptions below cover scripts developed or discussed in this project. Some scripts may need to be copied into your checkout; the precise contents of older inspection scripts have not been independently verified against your current repository.

## Environment and dependencies

The working configuration used Key4hep `2026-04-08`, Gaudi 40.2, ROOT 6.38.04, k4SimGeant4 0.1.0pre17, and FCC-hh v3.03 geometry. The custom `SimG4CharginoFtfpBert` component must be built and discoverable by Gaudi. `FCCDETECTORS` must point to the detector installation. Python analysis needs `podio`; the efficiency script also needs PyROOT, NumPy, pandas and matplotlib.

## Simulation files

### `options/run_chargino_fcchh.py`

The original working Gaudi steering file. It configures the `MomentumRangeParticleGun` (PDG codes `1000024` and `-1000024`), HepMC-to-EDM4hep conversion, the custom Geant4 physics list, the simulation algorithm and EDM4hep output. The supplied configuration generates 1,000 events at 1,000 GeV, with polar angle 1.50–1.64 radians, neutralino mass 3,000 GeV, mass splitting 0.165 GeV and chargino proper lifetime 0.2 ns.

### `options/run_chargino_fcchh_updated.py`

The updated steering file preserves the simulation and particle-history configuration but reads its settings from environment variables:

| Environment variable | Default | Purpose |
|---|---|---|
| `N_EVENTS` | `1000` | Number of events |
| `OUTPUT` | `chargino_decay_truth_SIM.root` | Output file |
| `NEUTRALINO_MASS_GEV` | `3000.0` | Neutralino mass |
| `MASS_SPLITTING_GEV` | `0.165` | Chargino–neutralino mass difference |
| `CHARGINO_LIFETIME_NS` | `0.2` | Proper lifetime |
| `STABLE_CHARGINO` | `False` | Turn off decay for a stable control sample |
| `MOMENTUM_MIN_GEV` | `1000.0` | Minimum gun momentum |
| `MOMENTUM_MAX_GEV` | `1000.0` | Maximum gun momentum |
| `THETA_MIN` | `1.50` | Minimum polar angle (radians) |
| `THETA_MAX` | `1.64` | Maximum polar angle (radians) |

Example:

```bash
N_EVENTS=10000 CHARGINO_LIFETIME_NS=1.0 \
MOMENTUM_MIN_GEV=1000 MOMENTUM_MAX_GEV=1000 \
OUTPUT=chargino_tau1ns_SIM.root \
k4run options/run_chargino_fcchh_updated.py
```

**Critical configuration detail:** `geantservice.physicslist = physics` and `geantservice.actions = actions` pass the *configured instances*, not tool-name strings. `SimG4FullSimActions` has `enableHistory=True` and `energyCut=0.0`. The particle-history output saver is already included in the detector configuration; do not add a second saver writing `SimParticleSecondaries`.

### `options/detector_fcc_hh_fixed_disTrack.py`

Local FCC-hh detector configuration imported by the steering file. It defines the simulation's detector and hit output tools. Barrel and endcap hit savers have different Gaudi names (`saveTrackerBarrelHits` and `saveTrackerEndcapHits`) to avoid a duplicate-tool collision. A single `SimG4SaveParticleHistory` saver persists `SimParticleSecondaries`. Keep this file in the `options/` directory alongside the steering file.

### `src/SimG4CharginoFtfpBert.cpp`

Custom FTFP_BERT-based physics-list component. It defines the neutralino and chargino masses, chargino lifetime, charged-particle multiple scattering and ionisation, and the simplified two-body decays `chi+ -> chi0 pi+` and `chi- -> chi0 pi-`. The `StableChargino` property disables decay for geometry tests. This is a simplified signal model, not a full decay model.

## Output collections

- `GenParticles`: generated input particles.
- `SimParticleSecondaries`: Geant4 particle history, including the chargino and its decay products.
- `TrackerBarrelReadout`: simulated barrel tracker hits.
- `TrackerEndcapReadout`: simulated endcap tracker hits.

In this k4SimGeant4 version, the particle-history code stores the **Geant4 track ID** in `MCParticle.simulatorStatus`. The tracker-hit saver stores the **same track ID** in `SimTrackerHit.quality` as a documented workaround. It does **not** populate `SimTrackerHit.particle`. Match hits using `hit.getQuality() == particle.getSimulatorStatus()`; do not dereference `hit.getParticle()`.

## Inspection and validation scripts

### `scripts/inspect_file.py`

General EDM4hep output inspector: check collection presence and event contents before interpreting the physics. Exact command-line options depend on your existing script. `podio-dump file.root` is a useful independent collection-level check.

### `scripts/summarise_tracker_hits.py`

Counts hits in each tracker readout and events with hits. Useful for confirming the simulation and comparing stable/decaying runs. **These are all-particle counts**, including pions and detector secondaries, so they are not chargino efficiency measurements.

### `scripts/summarise_hit_radii.py`

Examines transverse hit radius `sqrt(x*x + y*y)` to understand detector coverage and diagnose unexpected hit distributions. Without truth filtering, it includes hits from all charged particles.

### `scripts/summarise_tracker_layers.py`

Uses DD4hep readout decoders to translate `cellID` to barrel `system/layer` or endcap `system/posneg/disc`, then counts distinct layers with hits. Earlier event-level layer counts mixed chargino and secondary hits and therefore cannot establish chargino survival.

### `scripts/inspect_particle_history.py`

Reads `SimParticleSecondaries` with the current podio API:

```python
from podio import root_io
reader = root_io.Reader(filename)
for event in reader.get("events"):
    particles = event.get("SimParticleSecondaries")
```

Prints particle PDG, Geant4 track ID, momentum and vertex. For the single-chargino gun, the neutralino and charged pion have the same production vertex, which identifies the chargino decay position. Parent/daughter relationships are not yet populated in this history collection.

### `scripts/inspect_tracker_truth.py`

Builds a dictionary from Geant4 track ID to `MCParticle` and labels tracker hits via `hit.getQuality()`. This distinguishes genuine chargino hits from pion/muon/other secondary hits. In a validated event, the chargino (G4 track 1) decayed at about 0.031 mm and made **no** tracker hits; the pion (track 2) and a secondary muon (track 36) accounted for all 12 barrel hits.

## Truth-level efficiency analysis

### `scripts/analyse_chargino_efficiency.py`

The analysis script previously provided in this tutorial performs these operations:

1. Load the FCC-hh DD4hep geometry and tracker readout decoders.
2. Find the unique chargino (`abs(PDG)==1000024`) in each event.
3. Locate the decay using the common vertex of the unique neutralino and appropriately charged pion.
4. Select only tracker hits with `quality == chargino.simulatorStatus`.
5. Decode hit layer IDs, count distinct chargino-hit layers, and record first/last hit radii.
6. Write event-level CSV and two plots.

Run:

```bash
python scripts/analyse_chargino_efficiency.py \
  chargino_decay_truth_SIM.root --output chargino_decay
```

Outputs:

| Output | Interpretation |
|---|---|
| `chargino_decay_events.csv` | One row per accepted event: chargino momentum, pT, eta, decay vertex/radius, hits and distinct layers |
| `chargino_decay_layers_vs_decay_radius.pdf` / `.png` | Scatter: each chargino's number of hit layers versus its decay radius |
| `chargino_decay_efficiency_vs_decay_radius.pdf` / `.png` | Binned fraction satisfying `N_layers >= 1,...,6` versus decay radius |
| `chargino_decay_efficiency.csv` | Bin boundaries, passing/total counts, efficiencies and approximate binomial errors |

The current plot uses 25 mm-wide radial bins. The errors are `sqrt(e*(1-e)/n)`, which can be misleading for sparse bins or efficiencies of 0 or 1; use proper binomial confidence intervals in a future update. The analysis assumes one chargino, one neutralino and one corresponding pion per event. It is not suitable without modification for realistic multi-particle signal events.

**Physics interpretation:** these are **truth-hit / geometric acceptance** plots, not reconstructed-track efficiencies. Hits from the decay pion are explicitly excluded.

## Lifetime scan

### `scripts/run_lifetime_scan.sh`

A proposed wrapper to run 10,000 events per lifetime for `0.05 0.1 0.2 0.5 1.0 2.0 5.0 10.0` ns. It keeps the momentum at 1,000 GeV and the polar angle in 1.50–1.64 radians, and writes separate ROOT outputs under `samples/lifetime_scan/` with logs under `logs/lifetime_scan/`.

**Important:** if you use the previously supplied wrapper, change its `k4run` command to point at `options/run_chargino_fcchh_updated.py` rather than the original steering file; otherwise the environment-variable overrides will not be applied.

```bash
chmod +x scripts/run_lifetime_scan.sh
./scripts/run_lifetime_scan.sh
```

For a 3 TeV chargino with 1 TeV momentum, `beta*gamma` is approximately 1/3 and the mean lab flight distance is approximately `100 mm × tau[ns]`. The lifetime scan populates a wider range of decay radii; it is **not** a physical lifetime distribution to merge unweighted. For physics predictions, use an appropriate signal spectrum and lifetime weighting.

## Tracker geometry and layer counting

For central tracks, observed barrel hit radii were approximately **25, 60, 102, 150, 264, 395, 529, 751, 931, 1136, 1321 and 1521 mm**. These are observed positions, **not a verified table of nominal layer radii**. Always use decoded `cellID` layer keys to distinguish layers; do not use radius alone as a layer identifier.

## Suggested validation sequence

1. Generate a small stable sample and confirm tracker hits are present.
2. Generate a decaying sample and confirm `SimParticleSecondaries` and tracker collections with `podio-dump`.
3. Inspect the chargino, neutralino and pion with `inspect_particle_history.py`.
4. Check hit truth labels with `inspect_tracker_truth.py`; verify pion hits are not counted as chargino hits.
5. Run `analyse_chargino_efficiency.py` and inspect its CSV, particularly early-decay events with zero chargino layers.
6. Only then run larger lifetime and kinematic scans.

## Planned next stages (not implemented yet)

- Expand plots from thresholds 1–6 to all 12 barrel layers.
- Determine exact nominal layer radii from the geometry XML.
- Produce layer-survival maps and acceptance versus decay radius, pT and eta.
- Add truth-assisted then realistic track finding and fitting; measure reconstruction efficiency relative to truth-reconstructable charginos.
- Eventually include realistic wino/higgsino production, pileup, backgrounds and selection efficiencies.

The eventual reconstruction efficiency is `N(reconstructed, truth-matched tracklets) / N(truth-reconstructable charginos)`, distinct from the truth-hit acceptance measured here.
