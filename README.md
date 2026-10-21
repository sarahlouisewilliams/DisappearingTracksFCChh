# FCC-hh disappearing-track tutorial — v0.2

This version fixes the build errors found with the **Key4hep 2026-04-08 / Gaudi 40.2**
stack and adds a first **physical Geant4 chargino decay**.

## What changed from v0.1

Two v0.1 build assumptions were wrong for the current stack:

1. `k4SimGeant4::SimG4Interface` is not the CMake target used by k4SimGeant4.
   Current k4SimGeant4 links its components against the plain `SimG4Interface`
   target, so this repository now does the same.

2. `GaudiKernel/ComponentFactory.h` is not present in Gaudi 40.2. The explicit
   include has been removed. The implementation now mirrors the current
   `SimG4FtfpBert` component style.

The build script also follows the current Key4hep pattern: build/install, then
run `k4_local_repo`, rather than expecting `install/setup.sh`.

## Physics implemented

The custom physics list starts from `FTFP_BERT` and defines:

- neutralino: PDG `1000022`, neutral and stable;
- chargino+: PDG `1000024`, charge +1;
- chargino-: PDG `-1000024`, charge -1.

Defaults reproduce the old FCC-hh tutorial model:

```text
m(chi0)       = 3000.000 GeV
m(chi+/-)     = 3000.165 GeV
Delta m       = 165 MeV
tau(chi+/-)   = 0.2 ns
```

and the Geant4 decay tables contain

```text
chi+ -> chi0 + pi+
chi- -> chi0 + pi-
```

with 100% branching fraction.

The old Saito tutorial used the same 165 MeV splitting and configurable chargino
lifetime; its example used `SimG4CharginoPhysicsTool`.

## Build

On LXPLUS / an Alma9 Key4hep machine:

```bash
cd fcchh-disappearing-track-tutorial-v2
source setup.sh
source build.sh
```

The important CMake link line is now:

```cmake
LINK
  Gaudi::GaudiKernel
  ${Geant4_LIBRARIES}
  SimG4Interface
```

not `k4SimGeant4::SimG4Interface`.

## Run

Start with 10 events:

```bash
k4run options/run_chargino_fcchh.py
```

The defaults in `options/run_chargino_fcchh.py` are:

```python
NEUTRALINO_MASS_GEV = 3000.0
MASS_SPLITTING_GEV = 0.165
CHARGINO_LIFETIME_NS = 0.2
STABLE_CHARGINO = False
```

For the old stable-particle/reweighting approach set:

```python
STABLE_CHARGINO = True
```

## Inspect the output

```bash
python3 scripts/inspect_file.py chargino_fcchh_SIM.root
```

The current FCCSW FCC-hh detector block writes tracker simulation hits to:

```text
TrackerBarrelReadout
TrackerEndcapReadout
```

## Check that the charginos really decay

```bash
python3 scripts/check_decay.py chargino_fcchh_SIM.root
```

This prints the chargino endpoint and daughter PDG IDs where they are retained in
the EDM4hep truth record.

For the physical decay mode we expect daughters corresponding to the neutralino
and charged pion.

## Important validation note

This code has been updated against the public current k4SimGeant4 interfaces and
specifically against the build errors from Key4hep 2026-04-08 / Gaudi 40.2.

I cannot execute the full Key4hep/CVMFS build in the packaging environment used
to create this archive. Therefore run the build first and report the *first*
compiler/configuration error if the stack exposes another release-specific API
difference.

## Next analysis stage

Once the 10-event decay test works, the efficiency study should use the **actual
Geant4 chargino endpoint** rather than sampling a decay radius offline.

The next repository revision should therefore:

1. identify the chargino in the saved MC truth;
2. obtain its endpoint / decay radius;
3. associate `SimTrackerHit`s to that chargino;
4. decode FCC-hh tracker `cellID`s;
5. count distinct layers before the decay;
6. measure efficiency vs `(r_decay, pT, eta)`;
7. subsequently add digitisation and genuine pattern recognition.

That is the appropriate bridge to reproducing the old TrickTrack disappearing-track
workflow in modern FCCSW/Key4hep.
