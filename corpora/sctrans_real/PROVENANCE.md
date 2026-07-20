# sctrans_real

**Source:** SCTrans dataset (Zhang et al., "Building Critical Testing Scenarios for
Autonomous Driving from Real Accidents", ICSE 2024 tooling line), Fudan seclab.
Zenodo: https://zenodo.org/records/8120048 (`SCTrans-data.zip`, downloaded 2026-07-20).
Record license: CC BY 4.0.

**Real-data pedigree.** This corpus is the strictly-real subset of SCTrans's 1,994
OpenSCENARIO 1.0 conversions, filtered by scenario-id prefix:

| Prefix | Files | Underlying recording |
|---|---|---|
| `DEU_AAH1-4` | 500 | inD dataset — drone recordings of Aachen intersections (levelXdata) |
| `DEU_Location*` | ~508 | highD dataset — drone recordings of German motorways (levelXdata) |
| `USA_US101`, `USA_Lanker`, `USA_Peach` | ~71 | NGSIM — US-101 / Lankershim / Peachtree camera recordings (US DOT) |

Total: 1,079 `.xosc` + 81 matching OpenDRIVE `.xodr` (referenced by relative name,
same directory). Excluded prefixes (`ZAM_*`, `ESP_*`, `CHN_*`, other `DEU_*` towns)
are CommonRoad hand-crafted or OSM/SUMO-generated — not real recordings.

**Caveats for triage.** The trajectories were machine-converted (CommonRoad → CARLA
scenario_runner dialect). Findings may reflect conversion artifacts rather than the
real behavior — such findings are still informative (the point of linting converted
suites) but are triaged separately from "physics of the recording" claims. Upstream
levelXdata terms restrict redistribution of the *raw* datasets; this benchmark vendors
only SCTrans's derived scenario files under the Zenodo record's CC BY 4.0, with this
attribution.
