# FCC-hh disappearing-chargino simulation and truth-assisted tracking

This repository develops a **Geant4-based feasibility study of disappearing chargino tracks** in an FCC-hh detector model. It covers particle-gun generation, full simulation, validation of magnetic bending, truth-assisted helix fitting, proper-lifetime scans, and a preliminary comparison of hit-count and consecutive-layer acceptance.

## Workflow at a glance

| Stage | Purpose | Main input | Main output | Status |
|---|---|---|---|---|
| 1. Full simulation | Generate charged winos/charginos and simulate tracker hits | `options/run_chargino_fcchh_updated.py`, custom physics-list library | `*_SIM.root`, Geant4 logs | Run successfully |
| 2. Stable-track validation | Check magnetic field and helix curvature | Stable-chargino simulation ROOT | Sagitta and fitted momentum diagnostics | Checked against analytic expectation |
| 3. Decaying-track study | Fit truth-associated hits from decaying charginos | Unstable-chargino simulation ROOT | `*_fit.csv`, diagnostic plots | Run successfully; 4-hit fit threshold is analysis-defined |
| 4. Lifetime scan | Repeat simulation and fitting for several lifetimes | Steering file, shell driver | Five ROOT files, five CSV files, logs | Completed at 10,000 events/lifetime |
| 5. Hit/layer acceptance | Compare total hit counts with first-four/five radial-layer requirements | Lifetime-scan ROOT files | Printed acceptance and `layer_acceptance.png` | Provisional geometry-based results; layer identity/truth matching to check |

## 1. Software and working directory

Run the commands below from the repository root, for example:

```bash
cd /eos/user/w/williams/WorkAreaPostOlivia/DisappearingTrack
```

The development environment used a Key4HEP/FCCSW stack with Gaudi, k4SimGeant4, DD4hep, ROOT, podio and Python. **Activate the same Key4HEP environment used to build the custom physics-list plugin before running `k4run` or the analysis scripts.** The exact setup command is installation-specific and is not reproduced here because it has not been verified against the current repository.

The custom physics-list module (`SimG4CharginoFtfpBert`, built as `libCharginoPhysics.so`) must be available to the runtime. It uses an FTFP_BERT base and defines the charged and neutral SUSY states. For unstable charginos it enables the decay χ± → χ⁰ π±; for stable validation runs it disables that decay.

Useful sanity checks:

```bash
which k4run
python -c 'from podio import root_io; print("podio OK")'
ls options/run_chargino_fcchh_updated.py
ls scripts/truth_assisted_tracking_decays.py
```

## 2. Full simulation: particle gun and Geant4

**Steering file:** `options/run_chargino_fcchh_updated.py`

The particle gun generates chargino states with PDG IDs `1000024` and `-1000024`. The development studies used masses of approximately 3000.165 GeV, a momentum around 1000 GeV, and directions near the transverse plane. Check the current steering-file values before interpreting the acceptance as a function of lifetime or boost.

Two important steering parameters are:

- `STABLE_CHARGINO`: stable validation versus decaying-chargino propagation.
- `CHARGINO_LIFETIME_NS`: proper lifetime for the decaying mode, supplied by the lifetime-scan shell script.

A typical invocation for a decaying sample is:

```bash
STABLE_CHARGINO=False CHARGINO_LIFETIME_NS=5 \
  k4run options/run_chargino_fcchh_updated.py
```

**Important:** The actual ROOT output path and number of events are set by the steering file and/or runtime options. Inspect those settings before a manual run to avoid overwriting an existing sample. The lifetime-scan driver described below manages per-lifetime outputs.

### Magnetic-field configuration: resolved issue

An earlier version of the steering file accidentally instantiated **two** `SimG4ConstantMagneticFieldTool` objects. The second assignment overwrote the correctly configured field. The duplicate assignment was removed, leaving a single field tool configured with:

```python
FieldOn = True
FieldComponentZ = 6.0 * units.tesla
IntegratorStepper = "G4ExactHelixStepper"
```

The exact Python property syntax depends on the local configuration object; these lines document the intended settings, not a complete standalone configuration block. **Do not reintroduce a second assignment to `geantservice.magneticField`.**

## 3. Stable-chargino validation

Run a stable sample using the stable-chargino setting in the steering file, then use the repository's stable-track diagnostics and truth-assisted helix fitting. The exact filenames/CLI flags of the standalone sagitta diagnostic have not been verified in the current repository, so consult the existing scripts rather than assuming a command here.

The following results were checked for the approximately 1 TeV transverse-momentum stable sample in the 6 T field:

| Quantity | Observed | Reference / interpretation |
|---|---:|---|
| Maximum absolute sagitta | ~0.4995 mm | Analytic expectation ~0.5014 mm for the tested chord |
| Mean truth transverse momentum | ~999.13 GeV | Generated sample |
| Mean fitted transverse momentum | ~1001.97 GeV | Truth-assisted helix fit |
| Median fitted transverse momentum | ~1002.47 GeV | Truth-assisted helix fit |
| Mean relative momentum residual | +0.2846% | Small positive bias, retained for now |
| Standard deviation of relative residual | ~0.5875% | Stable-track reference performance |

These checks established that the previously missing curvature was a magnetic-field configuration issue. They do **not** validate realistic hit measurement errors or pattern recognition.

## 4. Decaying-chargino truth-assisted tracking

**Script:** `scripts/truth_assisted_tracking_decays.py`

**Input:** Geant4 simulation ROOT containing generated/secondary particles and tracker hit collections.

**Output:** A per-event CSV (`*_fit.csv`) with tracking and truth information, including hit multiplicity, decay position/radius, fit success, and momentum residual quantities. The precise column names and command-line flags must be checked with the installed version:

```bash
python scripts/truth_assisted_tracking_decays.py --help
```

The current fitting study uses **at least four truth-associated hits** as its minimum fitting threshold. This is an analysis choice, **not** a built-in FCC-hh detector reconstruction requirement.

**Diagnostic plotting script:** `scripts/check_decaying_chargino_tracking.py`

Use its `--help` output to confirm the expected CSV argument and output options:

```bash
python scripts/check_decaying_chargino_tracking.py --help
```

The study produced plots of hit multiplicity versus decay radius, fraction with at least four hits versus radius, fit-success fraction versus radius, and momentum residual versus decay radius or hit multiplicity.

**Observed behaviour:** At a 5 ns lifetime, the fit-success fraction closely followed the fraction of events with at least four associated hits. Short tracks had broader, positively biased momentum residuals; longer tracks approached the stable-track performance.

## 5. Lifetime scan: simulation and fitting

**Driver:** `scripts/run_chargino_lifetime_scan.sh`

The scan was completed at **10,000 generated events per lifetime** for:

```text
0.2, 1, 2, 5, 10 ns
```

Run from the repository root:

```bash
bash scripts/run_chargino_lifetime_scan.sh
```

The driver calls `k4run` with the appropriate lifetime and then runs the truth-assisted tracking script. It saves simulation logs, fit logs, simulation ROOT files, and fit CSVs under `results/lifetime_scan/`. **The existing samples have already been generated; do not rerun this command just to make plots.** Check the driver's skip-existing logic and filenames before any regeneration.

### Expected files

```text
results/lifetime_scan/
  chargino_tau0p2ns_SIM.root
  chargino_tau0p2ns_fit.csv
  chargino_tau1ns_SIM.root
  chargino_tau1ns_fit.csv
  chargino_tau2ns_SIM.root
  chargino_tau2ns_fit.csv
  chargino_tau5ns_SIM.root
  chargino_tau5ns_fit.csv
  chargino_tau10ns_SIM.root
  chargino_tau10ns_fit.csv
  tau0p2ns_simulation.log
  tau0p2ns_fit.log
  ... corresponding logs for the other lifetimes ...
```

**Filename warning:** Some local files have appeared with a `tau1p0ns` tag rather than `tau1ns`. Check the actual names with `ls results/lifetime_scan/` and keep the Python and Bash conventions consistent. The robust Python convention for numeric lifetimes is:

```python
tag = f'tau{format(float(tau), "g").replace(".", "p")}ns'
```

This produces `tau0p2ns`, `tau1ns`, `tau2ns`, `tau5ns`, `tau10ns`.

### Plot the lifetime scan

**Script:** `scripts/plot_chargino_lifetime_scan.py`

This script reads the existing per-event fit CSVs. Its exact CLI flags were not confirmed in the discussion; check:

```bash
python scripts/plot_chargino_lifetime_scan.py --help
```

Outputs produced during development:

- `lifetime_scan_fit_efficiency.png`: successful truth-assisted fits / generated events versus lifetime.
- `lifetime_scan_momentum_performance.png`: conditional fitted transverse-momentum residual, with 16th–84th percentile intervals.
- `lifetime_scan_hit_acceptance.png`: generated-event acceptance for thresholds ≥4, ≥5, ≥6, ≥7, ≥8 associated hits.

These image basenames describe the plots shared during development; their output directory is determined by the local plotting script.

**Interpretation:** Fit efficiency is nearly identical to the ≥4-associated-hit fraction. Momentum residuals improve with increasing lifetime **among successfully fitted tracks**; these residuals should not be interpreted as the performance of all generated events.

## 6. Inspect simulated tracker layers

**Script:** `scripts/inspect_chargino_hit_layers.py`

A first inspection printed the positions and `cellID` values of selected hits. The diagnostic script was then extended locally to report aggregate hit-count and layer-based acceptances; the final local contents should be checked because the same filename was used for both purposes during development.

An example inspection invocation was:

```bash
python scripts/inspect_chargino_hit_layers.py \
  results/lifetime_scan/chargino_tau1p0ns_SIM.root \
  --events 20
```

The observed barrel-hit radii formed five well-separated groups:

| Provisional radial layer | Approximate hit radius |
|---|---:|
| 1 | 25–27 mm |
| 2 | 60–63 mm |
| 3 | 100–102 mm |
| 4 | 150–152 mm |
| 5 | ~264 mm |

**These are provisional radial groups, not yet decoded DD4hep layer identifiers.** In particular, it has **not** been established whether the ~264 mm layer belongs to the pixel detector.

### Provisional acceptance definitions

For each event, let `H` be the set of radial-layer indices assigned to selected barrel hits:

- `>=4 hits`: at least four selected barrel hits, regardless of layer.
- `first 4 layers`: `{1,2,3,4} ⊆ H`.
- `>=5 hits`: at least five selected barrel hits.
- `first 5 layers`: `{1,2,3,4,5} ⊆ H`.

The provisional radial windows used in the analysis were:

```python
LAYER_WINDOWS_MM = [
    (20.0, 35.0),
    (55.0, 70.0),
    (95.0, 110.0),
    (145.0, 160.0),
    (255.0, 275.0),
]
```

These windows should be replaced by detector-geometry/cell-ID decoding before a physics interpretation.

For the **1 ns, 10,000-event sample**, the provisional calculation returned:

| Selection | Acceptance | Selected events |
|---|---:|---:|
| ≥4 associated barrel hits | 0.2469 | 2,469 |
| First four radial layers | 0.2215 | 2,215 |
| ≥5 associated barrel hits | 0.1041 | 1,041 |
| First five radial layers | 0.0713 | 713 |

The difference between hit count and layer count is larger for the five-layer requirement, especially at shorter lifetimes.

## 7. Plot hit-count versus layer-based acceptance

**Script:** `scripts/plot_chargino_layer_acceptance.py`

**Input:** The five existing `chargino_tau*ns_SIM.root` simulation files.

**Output:** `results/lifetime_scan/layer_acceptance.png`, plus printed acceptances for each lifetime.

Run:

```bash
python scripts/plot_chargino_layer_acceptance.py \
  --input-dir results/lifetime_scan \
  --output results/lifetime_scan/layer_acceptance.png
```

Optionally restrict the event count with `--events N` if supported by the local version. With no limit, the script processes all available events.

The plot contains four curves: ≥4 hits, first four radial layers, ≥5 hits, and first five radial layers. The layer-based curves lie below the corresponding hit-count curves; the separation is largest for short-lived charginos.

**Critical qualification:** The provisional scripts used `hit.getQuality() == g4id`, with `g4id` obtained from `particle.getSimulatorStatus()`, as a putative truth-association test. **This has not been demonstrated to be a valid Geant4 track-ID association.** The observed numbers are therefore diagnostic only. Before treating these as validated physical acceptances, compare against the association method used by the original tracking script and inspect the EDM4hep hit-to-particle relations, where available.

## 8. Validation status and outstanding work

### Checked in development

- Custom chargino physics-list module builds and runs, with stable and unstable configurations.
- Geant4 transport in a 6 T magnetic field produces the expected stable-chargino curvature after removal of the duplicate field assignment.
- Stable truth-assisted helix fit gives transverse momentum close to the known input, with a small residual bias.
- Decaying-chargino fits, 10,000-event lifetime samples, and lifetime-scan plotting execute successfully.
- Radial hit groups are distinguishable and a provisional layer-acceptance comparison can be calculated from the saved ROOT samples.

### Not yet validated / not implemented

1. **Truth association for layer scripts:** confirm the correct relation between each simulated tracker hit and the chargino; do not assume `getQuality()` encodes a Geant4 track ID.
2. **DD4hep layer identities:** decode `cellID` using the active readout description; confirm barrel subsystem boundaries and the fifth layer's technology.
3. **Comparison with the 2019 study:** its four-/five-**pixel**-layer definitions are not automatically equivalent to the four/five radial groups used here.
4. **Realistic production:** replace the fixed-momentum central particle gun with a chargino momentum and pseudorapidity spectrum from a production sample.
5. **Realistic reconstruction:** digitisation, pattern recognition, fake tracks, pileup, timing, reconstruction-quality selections, and physics backgrounds are not represented by truth-assisted fitting.
6. **Sensitivity:** no discovery significance or exclusion reach has yet been calculated.

## 9. Suggested next checks

1. Inspect `options/run_chargino_fcchh_updated.py` to identify the exact DD4hep geometry XML and readout configuration.
2. Decode tracker hit `cellID` values into subsystem and layer fields; check whether the fifth radial group is a pixel layer.
3. Reuse the **validated** hit-to-chargino association from `scripts/truth_assisted_tracking_decays.py` in the layer-acceptance script, rather than using an unverified quality-field comparison.
4. Reproduce the acceptance plots with verified pixel-layer requirements, then consider realistic chargino production kinematics.

## 10. Quick command reference

```bash
# From the repository root

# Verify key scripts and the podio environment
python -c 'from podio import root_io; print("podio OK")'

# Inspect hit radii and cell IDs in an existing sample
python scripts/inspect_chargino_hit_layers.py \
  results/lifetime_scan/chargino_tau1p0ns_SIM.root --events 20

# Plot provisional hit-count vs radial-layer acceptance
python scripts/plot_chargino_layer_acceptance.py \
  --input-dir results/lifetime_scan \
  --output results/lifetime_scan/layer_acceptance.png

# Inspect available arguments for the lifetime plotting and tracking scripts
python scripts/plot_chargino_lifetime_scan.py --help
python scripts/truth_assisted_tracking_decays.py --help
python scripts/check_decaying_chargino_tracking.py --help

# Regenerate the complete lifetime scan ONLY if necessary
# bash scripts/run_chargino_lifetime_scan.sh
```

### Reference

Saito, Sawada, Terashi and Asai, *Discovery reach for wino and higgsino dark matter with a disappearing track signature at a 100 TeV pp collider*, **Eur. Phys. J. C 79, 469 (2019)**, [arXiv:1901.02987](https://arxiv.org/abs/1901.02987).

The 2019 paper motivates studying short-track reconstruction and four-/five-pixel-layer requirements. The present work is a preliminary FCC-hh detector and truth-assisted tracking exercise, **not** a reproduction of the paper's complete reconstruction or background analysis.
