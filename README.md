# FCC-hh disappearing-chargino simulation tutorial

This repository is a staged tutorial for generating individual charged winos/charginos, propagating them through an FCC-hh detector with Geant4, inspecting their tracker hits and decay products, and evaluating *truth-assisted* track fitting. It is **not** yet a realistic disappearing-track reconstruction or physics-sensitivity analysis.

The tutorial has two parts:

1. **Part 1 — Generation, full simulation and truth-hit acceptance.** Configure a chargino particle gun and custom Geant4 physics list; save particle history and tracker hits; identify which hits came from the chargino rather than its decay products; study hit/layer acceptance versus decay radius.
2. **Part 2 — Truth-assisted tracking.** First validate the 6 T magnetic field and the helix fit using **stable charginos**. Only after that control sample works, generate **decaying charginos** and measure fit efficiency and momentum performance versus decay radius and hit multiplicity.

> **Important correction to earlier versions:** the FCC-hh solenoid geometry does not by itself guarantee that Geant4 propagates particles in a magnetic field. The simulation steering must attach a correctly configured `SimG4ConstantMagneticFieldTool` to `SimG4Svc`. 

## Environment and dependencies

The tested environment was Key4hep `2026-04-08` (Gaudi 40.2, ROOT 6.38.04, k4SimGeant4 0.1.0pre17), with FCC-hh v3.03 geometry. The custom `SimG4CharginoFtfpBert` Gaudi component must be built and discoverable. The `FCCDETECTORS` environment variable must point to the detector installation. Python post-processing requires `podio`, NumPy, SciPy, pandas and matplotlib; the original DD4hep-based layer-acceptance script also uses PyROOT/DD4hep.

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

## 1. Part 1 — Chargino generation and Geant4 simulation

### 1.1 Physics model

`MomentumRangeParticleGun` generates one charged particle per event, with PDG ID `1000024` (positive chargino) or `-1000024` (negative chargino). The generated particles are passed through `GenAlg` and `HepMCToEDMConverter` into `GenParticles`.

`SimG4CharginoFtfpBert` extends `FTFP_BERT` with a neutralino and charged charginos. The simplified unstable mode includes

```text
chi+ -> chi0 + pi+
chi- -> chi0 + pi-
```

with the proper lifetime specified by `CHARGINO_LIFETIME_NS`. `STABLE_CHARGINO=True` disables chargino decay but retains charged-particle transportation, multiple scattering and ionisation. This is a simplified single-particle signal model, not a full FCC-hh production simulation.

The recommended steering supports:

| Environment variable | Default | Meaning |
|---|---:|---|
| `N_EVENTS` | `1000` | Generated events |
| `OUTPUT` | `chargino_decay_truth_SIM.root` | Output EDM4hep ROOT file |
| `NEUTRALINO_MASS_GEV` | `3000.0` | Neutralino mass |
| `MASS_SPLITTING_GEV` | `0.165` | Chargino minus neutralino mass |
| `CHARGINO_LIFETIME_NS` | `0.2` | Chargino proper lifetime when unstable |
| `STABLE_CHARGINO` | `False` | Disable decay for a control sample |
| `MOMENTUM_MIN_GEV` | `1000.0` | Minimum generated momentum magnitude |
| `MOMENTUM_MAX_GEV` | `1000.0` | Maximum generated momentum magnitude |
| `THETA_MIN` | `1.50` | Minimum polar angle, radians |
| `THETA_MAX` | `1.64` | Maximum polar angle, radians |

The gun sets **total momentum** to 1 TeV; the transverse momentum is close to 1 TeV because the polar-angle range is near the transverse plane.

### 1.2 Required magnetic-field configuration — applies to BOTH stable and decaying samples

In `options/run_chargino_fcchh_updated.py`, add the import and **one** field instance:

```python
from Configurables import SimG4ConstantMagneticFieldTool
from GaudiKernel import SystemOfUnits as units

field = SimG4ConstantMagneticFieldTool("CharginoField")
field.FieldOn = True
field.FieldComponentX = 0.0 * units.tesla
field.FieldComponentY = 0.0 * units.tesla
field.FieldComponentZ = 6.0 * units.tesla
field.IntegratorStepper = "G4ExactHelixStepper"
```

Then attach **that same configured instance** to the Geant4 service:

```python
geantservice = SimG4Svc("SimG4Svc")
geantservice.detector = "SimG4DD4hepDetector"
geantservice.magneticField = field
geantservice.physicslist = physics

# Retain the existing history/actions configuration.
actions = SimG4FullSimActions("FullSimActions")
actions.enableHistory = True
actions.energyCut = 0.0
geantservice.actions = actions
app.ExtSvc += [geantservice]
```

**Delete any later block resembling:**

```python
# WRONG: replaces the configured field with an unconfigured tool
field = SimG4ConstantMagneticFieldTool("MagneticField")
geantservice.magneticField = field
```

This exact overwrite caused the original stable-chargino sample to have nearly straight tracks and wildly overestimated fitted momentum. In the corrected sample, the measured sagitta agrees with the 6 T expectation. A constant 6 T field is a *controlled tutorial approximation*, not a verified full FCC-hh field map. The `FieldRMax` and `FieldZMax` properties need not be set for the validated configuration.

**Check the steering before running:**

```bash
grep -n -E 'SimG4ConstantMagneticFieldTool|magneticField|FieldOn|FieldComponent' \
  options/run_chargino_fcchh_updated.py
```

There should be one field-tool instantiation and one assignment to `geantservice.magneticField`.

### 1.3 Output collections and truth association

The output contains `GenParticles`, `SimParticleSecondaries`, `TrackerBarrelReadout`, and `TrackerEndcapReadout`. The local `detector_fcc_hh_fixed_disTrack.py` sets up the tracker hit savers and a single particle-history saver; do not add a duplicate `SimG4SaveParticleHistory` tool.

In the tutorial's current k4SimGeant4 configuration, `MCParticle.simulatorStatus` holds the Geant4 track ID and `SimTrackerHit.quality` holds the same ID. Associate chargino hits using:

```python
chargino_g4_id = chargino.getSimulatorStatus()
chargino_hits = [h for h in hits if h.getQuality() == chargino_g4_id]
```

Do **not** assume `SimTrackerHit.particle` is populated in these outputs. Do not count all tracker hits as chargino hits: charged pions and secondary particles can leave hits after the chargino disappears.

### 1.4 Initial decaying-sample inspection and truth-hit acceptance

```bash
mkdir -p samples results
STABLE_CHARGINO=False CHARGINO_LIFETIME_NS=1.0 N_EVENTS=10000 \
  OUTPUT=samples/chargino_tau1ns_6T_SIM.root \
  k4run options/run_chargino_fcchh_updated.py

podio-dump samples/chargino_tau1ns_6T_SIM.root
python scripts/inspect_particle_history.py samples/chargino_tau1ns_6T_SIM.root
python scripts/inspect_tracker_truth.py samples/chargino_tau1ns_6T_SIM.root

python scripts/analyse_chargino_efficiency.py \
  samples/chargino_tau1ns_6T_SIM.root --output results/chargino_tau1ns
```

The acceptance analysis counts **truth-associated chargino layers** and produces `*_events.csv`, `*_efficiency.csv`, `*_layers_vs_decay_radius.{png,pdf}` and `*_efficiency_vs_decay_radius.{png,pdf}`. This measures layer acceptance, not track reconstruction. The decay location is inferred from the common production vertex of the neutralino and same-sign pion, since the saved history does not reliably populate parent/daughter links. The original script assumes one chargino and the corresponding decay products per event.

## 2. Part 2 — Truth-assisted tracking and disappearing tracks

**Workflow:** (A) generate a stable control sample -> (B) validate magnetic bending and momentum fit -> (C) generate decaying samples -> (D) evaluate fit efficiency and resolution versus decay radius/hit multiplicity.

The tracking scripts fit truth-associated **Geant4 hit positions**, not reconstructed digitised hits. The xy trajectory is fitted to a circle, then z is fitted versus transverse arc length. With a uniform solenoidal field:

\[
p_T\,[\mathrm{GeV}] = 0.000299792458\,|B_z\,[\mathrm{T}]|\,R\,[\mathrm{mm}].
\]

The default fit threshold is **four chargino hits**. This is an algorithmic requirement for this diagnostic, not a detector-quality disappearing-track definition.

### 2.1 Stage 2A — Generate a **stable** chargino control sample

Always validate stable particles before attempting a lifetime scan. Stable mode is controlled by `STABLE_CHARGINO=True`; the lifetime setting is irrelevant while decay is disabled.

```bash
mkdir -p samples results
STABLE_CHARGINO=True N_EVENTS=1000 \
  MOMENTUM_MIN_GEV=1000 MOMENTUM_MAX_GEV=1000 \
  OUTPUT=samples/chargino_stable_6T_SIM.root \
  k4run options/run_chargino_fcchh_updated.py
```

This generates 1 TeV-momentum positive and negative charginos, near the transverse plane, and propagates them through the tracker **without decay**. The stable sample isolates magnetic bending and fit behaviour from loss of hits due to decay.

### 2.2 Stage 2B — Validate sagitta and fitted momentum

Use the stable-fit script **with the sagitta diagnostic** (the `truth_assisted_tracking.py` from the sagitta-enabled Stage 2 package):

```bash
python scripts/truth_assisted_tracking.py \
  samples/chargino_stable_6T_SIM.root \
  --bz-tesla 6.0 \
  --output results/stable_6T_truth_fit.csv

python scripts/plot_truth_assisted_tracking.py \
  results/stable_6T_truth_fit.csv \
  --output-prefix results/stable_6T
```

For a 1 TeV transverse momentum in 6 T, the expected curvature radius is approximately

\[
R \simeq \frac{1000}{0.000299792458\times6}
  \simeq 5.56\times10^5\ \mathrm{mm}.
\]

For the observed ~1.49 m transverse chord, the expected sagitta is about 0.50 mm. The sagitta diagnostic is independent of the circle fit and is therefore the first test of whether the simulated trajectories actually bend.

**Observed validation results (100-event corrected-field sample):**

| Quantity | Result |
|---|---:|
| Mean maximum absolute sagitta | 0.499484 mm |
| Mean expected sagitta | 0.501422 mm |
| Mean generated transverse momentum | 999.128 GeV |
| Mean fitted transverse momentum | 1001.971 GeV |
| Mean fitted radius | 557,036 mm |
| Mean relative momentum residual | +0.2846% |
| Standard deviation of relative momentum residual | 0.5875% |
| Median number of hits (earlier 1000-event stable sample) | 12 |

The mean signed sagitta can be close to zero because positive and negative charginos bend in opposite directions. Inspect absolute sagitta or separate the two charges.

**Known limitation:** the small +0.28% residual bias is documented but not corrected. Do not extrapolate the ~0.59% truth-assisted residual width to a realistic FCC-hh detector tracking resolution. A very small `chi2_ndof` does not validate detector hit uncertainties, because the script uses nominal effective hit errors without full digitisation.

**Failure mode discovered during development:** before the duplicate field tool was removed, the maximum sagitta was only ~0.003 mm (rather than ~0.5 mm) and the median fitted momentum was ~130 TeV. If this happens again, check the `SimG4Svc.magneticField` assignment before debugging the circle fitter.

### 2.3 Stage 2C — Generate **decaying** charginos

Only proceed once the stable sample passes the sagitta and momentum checks. Set `STABLE_CHARGINO=False` and specify a nonzero proper lifetime. A useful first sample is 5 ns:

```bash
STABLE_CHARGINO=False CHARGINO_LIFETIME_NS=5.0 N_EVENTS=10000 \
  MOMENTUM_MIN_GEV=1000 MOMENTUM_MAX_GEV=1000 \
  OUTPUT=samples/chargino_decay_tau5ns_6T_SIM.root \
  k4run options/run_chargino_fcchh_updated.py
```

For a ~3 TeV chargino with 1 TeV momentum, `beta*gamma ≈ 1/3`, so the mean laboratory flight distance is approximately `100 mm × lifetime[ns]`. At 5 ns this is ~500 mm. A 0.2 ns sample has mean flight distance ~20 mm and is therefore expected to contain many zero-hit charginos. The **transverse** decay radius is not identical to the 3D flight distance, though they are close for the near-transverse gun used here.

The decay produces a neutralino and charged pion. **Only hits belonging to the original chargino** should enter its track fit; pion hits must be excluded even when the pion continues through the tracker.

### 2.4 Stage 2D — Fit decaying tracks and measure efficiency

```bash
python scripts/truth_assisted_tracking_decays.py \
  samples/chargino_decay_tau5ns_6T_SIM.root \
  --bz-tesla 6.0 \
  --output results/decay_tau5ns_fit.csv

python scripts/plot_decaying_chargino_tracking.py \
  results/decay_tau5ns_fit.csv \
  --output-prefix results/decay_tau5ns
```

The decaying-fit script writes one row per event with a uniquely identified chargino, **including zero-hit and too-few-hit events**. Fields include `decay_r_mm`, `decay_status`, `n_hits`, `fit_status`, `fitted_pt_gev`, `truth_pt_gev`, `first_hit_r_mm`, `last_hit_r_mm`, and the sagitta diagnostics where enough hits exist. Missing or ambiguous decay-product matches are flagged rather than assigned an artificial decay radius of zero.

The plotting script produces:

| Output | Interpretation |
|---|---|
| `results/decay_tau5ns_efficiency.csv` | Counts and fit fraction by decay-radius bin |
| `results/decay_tau5ns_efficiency.png` | Fit fraction versus transverse decay radius |
| `results/decay_tau5ns_pt_residual_vs_radius.png` | Relative fitted-momentum residual versus decay radius |
| `results/decay_tau5ns_pt_residual_vs_hits.png` | Relative fitted-momentum residual versus chargino hit count |

For each decay-radius bin, the plotted quantity is

\[
\epsilon_{\mathrm{fit}}(r) =
\frac{N(\text{unique chargino, matched decay, successful fit in bin})}
     {N(\text{unique chargino, matched decay in bin})}.
\]

This is a **conditional truth-assisted fit fraction**, not an inclusive reconstruction efficiency. Events with unmatched/ambiguous decay vertices are excluded from the radius-binned denominator, and events lacking a uniquely identified chargino are not written to the CSV. The script defaults to plotting only bins with at least 10 denominator events. Momentum residual plots are necessarily conditional on a successful fit; they do not describe the failed short-track population.

### 2.5 Lifetime scan

Once 5 ns is understood, repeat the same procedure for `0.2`, `1`, `2`, `5` and `10` ns. Keep geometry, field, particle masses, generated momentum and theta, hit matching, and fit settings unchanged. Use a distinct ROOT file and CSV for each lifetime; do not silently combine samples with different lifetime distributions.

The original `scripts/run_lifetime_scan.sh`, if present, may need updating to call `options/run_chargino_fcchh_updated.py` and to use the corrected 6 T steering. Check its contents before using it.

## 3. How to interpret the results

| Quantity | What it establishes | What it does **not** establish |
|---|---|---|
| Truth-associated tracker hit count | Chargino's simulated hit coverage | Whether a tracking algorithm finds a track |
| Number of distinct tracker layers | Layer acceptance before decay | Track quality after digitisation |
| Sagitta vs expected sagitta | Magnetic bending and propagation consistency | Realistic momentum resolution |
| Stable-sample fitted momentum | Sanity check of circle/helix fitter | Full reconstruction performance |
| Fit fraction vs decay radius | Availability of enough ideal truth hits and successful numerical fits | Realistic disappearing-track efficiency |
| Momentum residual vs hits | Lever-arm dependence among fitted truth tracks | Performance for failed tracks or fakes |

Future stages should introduce digitisation/hit smearing, realistic pattern recognition, track-quality criteria, material/field-map refinements, and eventually signal kinematics, pileup and backgrounds. A fully realistic tracking efficiency needs a carefully defined truth-reconstructable denominator and a reconstructed, truth-matched track numerator.

## 4. Troubleshooting checklist

- **Nearly straight stable tracks / fitted momentum ~100 TeV:** confirm only one configured field tool is attached to `SimG4Svc`; rerun **both** simulation and fit, and check file timestamps and input paths.
- **No chargino hits but many tracker hits:** inspect Geant4 IDs; hits may belong to charged decay pions or other secondaries.
- **Missing decay radius:** check the neutralino and same-sign pion in `SimParticleSecondaries`; the tutorial infers the vertex from their common production point.
- **Few fitted decaying charginos:** inspect `n_hits` and `fit_status` before changing the fit; short-lived charginos may decay before reaching four layers/hits.
- **Very large fitted momentum for short tracks:** a small sagitta and short lever arm make curvature numerically poorly constrained; check fit residuals versus hit count and decay radius.
- **Inconsistent results after a code edit:** ensure the ROOT sample was regenerated using the new steering and the CSV was regenerated from that specific ROOT file.

## 5. Recommended order for a new user

1. Build the custom chargino physics-list component and confirm the Key4hep/FCC-hh environment.
2. Apply the **single 6 T field** fix to `run_chargino_fcchh_updated.py`.
3. Generate a **stable** 1 TeV sample and verify ~0.5 mm sagitta and ~1 TeV fitted momentum.
4. Generate a **5 ns decaying** sample, inspect particle history and confirm charged-pion hits are excluded.
5. Produce truth-hit acceptance and truth-assisted fit-efficiency plots.
6. Extend to a lifetime scan, then revisit numerical fit bias and realism only as needed.
