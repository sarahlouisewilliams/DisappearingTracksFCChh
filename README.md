# FCC-hh disappearing-chargino simulation tutorial

This tutorial generates individual charginos, simulates their decays in the FCC-hh detector with Geant4, persists particle history and tracker hits, and studies **truth-level** layer acceptance. **Track reconstruction is not yet included.**

## Environment and dependencies

The working configuration used Key4hep `2026-04-08`, Gaudi 40.2, ROOT 6.38.04, k4SimGeant4 0.1.0pre17, and FCC-hh v3.03 geometry. The custom `SimG4CharginoFtfpBert` component must be built and discoverable by Gaudi. `FCCDETECTORS` must point to the detector installation. Python analysis needs `podio`; the efficiency script also needs PyROOT, NumPy, pandas and matplotlib.

## Quick reference: script inputs and outputs

Paths in the examples are relative to the repository root. The simulation output filename is configurable; `chargino_decay_truth_SIM.root` is the default. Inspection scripts normally print to the terminal and do not create files. For older inspection utilities, the exact CLI has not been verified against your local copies.

| Script | Input files / configuration | Output files or terminal output |
|---|---|---|
| `options/run_chargino_fcchh.py` | Built custom physics-list component; `detector_fcc_hh_fixed_disTrack.py`; detector geometry; hard-coded gun settings | `chargino_decay_truth_SIM.root` (default in original script) |
| `options/run_chargino_fcchh_updated.py` | Same dependencies; environment variables for event count, lifetime, masses, momentum and angles | EDM4hep ROOT file named by `OUTPUT` (default `chargino_decay_truth_SIM.root`) |
| `options/detector_fcc_hh_fixed_disTrack.py` | Installed DD4hep detector geometry and readout configuration | No standalone file; configures Geant4 hit/history collections in the simulation output |
| `src/SimG4CharginoFtfpBert.cpp` | Source code, build environment; steering-supplied physics parameters at runtime | Compiled Gaudi component/library, not an event-data file |
| `scripts/inspect_file.py` | Simulation `.root` | Terminal inspection of event/collection content; exact CLI depends on local script |
| `scripts/summarise_tracker_hits.py` | Simulation `.root` | Terminal event/readout hit-count summary |
| `scripts/summarise_hit_radii.py` | Simulation `.root` | Terminal hit-radius summary |
| `scripts/summarise_tracker_layers.py` | Simulation `.root`; DD4hep geometry/readout decoder | Terminal distinct-layer summary |
| `scripts/inspect_particle_history.py` | Simulation `.root` with `SimParticleSecondaries` | Terminal particle-history table (PDG, G4 ID, momentum, vertex) |
| `scripts/inspect_tracker_truth.py` | Simulation `.root` with `SimParticleSecondaries` and tracker readouts | Terminal truth-matched hit table |
| `scripts/analyse_chargino_efficiency.py` | One simulation `.root`; DD4hep geometry | Event CSV, efficiency CSV, scatter plot PDF/PNG, efficiency plot PDF/PNG |
| `scripts/run_lifetime_scan.sh` | Updated steering file, lifetime list and run settings; detector and compiled component | One `.root` and one `.log` per lifetime, in `samples/lifetime_scan/` and `logs/lifetime_scan/` |

### How the files flow through the tutorial

```text
run_chargino_fcchh_updated.py
  + detector_fcc_hh_fixed_disTrack.py
  + compiled SimG4CharginoFtfpBert component
                  |
                  v
       chargino_decay_truth_SIM.root
                  |
        +---------+--------------------+
        |                              |
        v                              v
 inspection / validation     analyse_chargino_efficiency.py
 (terminal output)                     |
                         +-------------+-------------+
                         |                           |
                         v                           v
                 *_events.csv                 *_efficiency.csv
                         +                           +
                    scatter PDF/PNG            efficiency PDF/PNG
```

### Example commands and file naming

Run a single simulation (writes the specified ROOT file):

```bash
N_EVENTS=10000 CHARGINO_LIFETIME_NS=1.0 \
OUTPUT=samples/chargino_tau1ns_SIM.root \
k4run options/run_chargino_fcchh_updated.py
```

Create `samples/` first if necessary. Inspect the output:

```bash
podio-dump samples/chargino_tau1ns_SIM.root
python scripts/inspect_particle_history.py samples/chargino_tau1ns_SIM.root
python scripts/inspect_tracker_truth.py samples/chargino_tau1ns_SIM.root
```

Produce the efficiency products:

```bash
mkdir -p results
python scripts/analyse_chargino_efficiency.py \
  samples/chargino_tau1ns_SIM.root \
  --output results/chargino_tau1ns
```

The last command writes exactly these six files:

```text
results/chargino_tau1ns_events.csv
results/chargino_tau1ns_efficiency.csv
results/chargino_tau1ns_layers_vs_decay_radius.pdf
results/chargino_tau1ns_layers_vs_decay_radius.png
results/chargino_tau1ns_efficiency_vs_decay_radius.pdf
results/chargino_tau1ns_efficiency_vs_decay_radius.png
```

The current analysis accepts **one simulation ROOT file per invocation**. The lifetime scan generates separate samples, which can be analysed individually; automated multi-file combination is not implemented yet.

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

---

# Part 2 — Truth-assisted tracking studies (prototype)

## Scope and status

Part 1 above covers the existing **truth-level simulation and hit studies**. Part 2 introduces a **standalone diagnostic helix fitter** using the simulated hit positions and known Geant4 particle identity. This is a *first tracking study*, not a completed detector reconstruction. It does **not** yet implement realistic digitisation, a Kalman/GenFit fitter, material-aware propagation, a detector field map, EDM4hep `Track` output, or truth-independent pattern recognition.

The implementation is intentionally separate from the working Gaudi simulation. It reads the existing `*_SIM.root` directly, so no changes to the custom physics list or detector configuration are needed.

## New scripts: inputs and outputs

| Script | Input | Output | Purpose |
|---|---|---|---|
| `scripts/truth_assisted_tracking.py` | `*_SIM.root` with `SimParticleSecondaries`, `TrackerBarrelReadout`, `TrackerEndcapReadout`; command-line B-field and resolution assumptions | `tracking_truth_fit.csv` (or `--output` filename) | Selects only chargino-associated Geant4 hits, fits an approximate 3D helix and compares with truth momentum |
| `scripts/plot_truth_assisted_tracking.py` | CSV from the preceding script | `tracking_pt_residual_vs_hits.png/.pdf`, `tracking_chi2_ndof.png/.pdf` (prefix configurable) | Diagnostic residual and fit-quality plots |

The updated simulation steering file, `options/run_chargino_fcchh_updated.py`, is included in this extension bundle. It still requires the **existing local** `options/detector_fcc_hh_fixed_disTrack.py` and compiled `SimG4CharginoFtfpBert` component. They are not included here, because the current versions were not supplied.

## How the truth-assisted fitter works

1. Read the EDM4hep event with `podio.root_io.Reader`.
2. Find exactly one MC particle with `abs(PDG) == 1000024` in `SimParticleSecondaries`.
3. Identify its Geant4 track ID from `MCParticle.getSimulatorStatus()`.
4. Collect barrel and endcap `SimTrackerHit` positions where `hit.getQuality() == chargino_id`. **This association depends on your verified custom hit saver**; it is not a general EDM4hep convention.
5. Sort hit positions by cylindrical radius, fit a transverse circle, and fit longitudinal position as a linear function of signed transverse arc length.
6. Estimate transverse momentum from the fitted curvature using `pT[GeV] = 0.000299792458 * |Bz[T]| * R[mm]`.
7. Write one CSV row per event, including the number of chargino hits, fit status, true/fitted momentum, fitted radius and approximate fit quality.

The fit uses the original **simulated hit positions**, with user-supplied effective resolutions only to scale the residuals. It does **not smear or digitise** the hits. Its chi-squared is a diagnostic, not a statistically calibrated tracking fit.

The method assumes an approximately uniform solenoidal `Bz`, outward-going non-looping trajectories, and a helix with negligible energy loss. It ignores material scattering and does not account for the full FCC-hh field map. In particular, high-momentum (~1 TeV) charginos have weak curvature, so circle fits can be poorly constrained, especially with only a few inner hits. Fit results must be treated as preliminary.

## Running Part 2

First produce a **stable-chargino** control sample with Part 1:

```bash
STABLE_CHARGINO=True N_EVENTS=1000 \
OUTPUT=chargino_stable_SIM.root \
k4run options/run_chargino_fcchh_updated.py
```

Then run the standalone fitter, supplying an **explicit Bz value appropriate to the detector region**. The example below uses `4.0 T` **only as an illustrative assumption**, not a verified FCC-hh detector value:

```bash
python scripts/truth_assisted_tracking.py \
  chargino_stable_SIM.root \
  --bz-tesla 4.0 \
  --min-hits 4 \
  --sigma-rphi-mm 0.01 \
  --sigma-z-mm 0.05 \
  --output results/stable_truth_fit.csv
```

Generate diagnostic plots:

```bash
python scripts/plot_truth_assisted_tracking.py \
  results/stable_truth_fit.csv \
  --output results/stable
```

Expected files:

```text
results/stable_truth_fit.csv
results/stable_pt_residual_vs_hits.png
results/stable_pt_residual_vs_hits.pdf
results/stable_chi2_ndof.png
results/stable_chi2_ndof.pdf
```

Repeat with a decaying sample:

```bash
STABLE_CHARGINO=False CHARGINO_LIFETIME_NS=0.2 \
N_EVENTS=10000 OUTPUT=chargino_decay_SIM.root \
k4run options/run_chargino_fcchh_updated.py

python scripts/truth_assisted_tracking.py \
  chargino_decay_SIM.root \
  --bz-tesla 4.0 \
  --output results/decay_truth_fit.csv
```

**Before interpreting fitted momenta**, replace the illustrative B-field value with a justified value or implement a field-map-aware propagator. The current script does not independently check the magnetic field in the geometry.

## Output CSV columns

- `event`, `chargino_g4_id`, `pdg`: event and chargino identity.
- `truth_pt_gev`, `truth_p_gev`: generated/simulation-truth momentum.
- `n_hits`: count of **chargino-associated** SimTrackerHits across barrel and endcap.
- `fit_status`: `ok`, `too_few_hits` or `fit_failed`.
- `fitted_radius_mm`, `fitted_pt_gev`, `fitted_p_gev`: fitted curvature and approximate momenta.
- `slope_dz_ds`: longitudinal slope along signed transverse arc length.
- `chi2`, `ndof`, `chi2_ndof`: approximate geometric-fit diagnostics.
- `first_hit_r_mm`, `last_hit_r_mm`: smallest and largest cylindrical hit radii in the fit.

A row with `too_few_hits` has blank fit fields; it is **not** a pattern-recognition failure. A truth-assisted fit can succeed even when a realistic track finder would fail.

## Suggested validation sequence

1. Run the stable 1 TeV central sample and check the `n_hits` distribution.
2. Inspect individual fit residuals and extreme fitted momenta; test sensitivity to hit count and assumed B field.
3. Run the decaying sample and compare fit success versus the number of **chargino** hits.
4. Add true detector digitisation, including local measurement coordinates, pixel/strip resolutions, and measurement covariances.
5. Replace the diagnostic circle/line fit with a proper GenFit/Kalman-style fit using the FCC-hh geometry, material and magnetic-field map.
6. Add pattern recognition and evaluate matched-track efficiency and fake rates separately from truth-hit acceptance.

## Dependencies

Part 2 requires Python with `numpy`, `scipy`, `podio`, `pandas`, and `matplotlib` available in the same compatible Key4hep environment. No custom reconstruction Gaudi component is required for this first prototype.

## Limitations and next milestone

This prototype **does not produce** `*_DIGI.root` or `*_REC.root` and does not write `edm4hep::Track` collections. The next milestone is a detector-aware digitisation and fitted-track pipeline, after verifying the exact algorithms and components installed in your Key4hep release. The original FCC-hh detector and physics-list source are deliberately not replaced by guessed configurations.
