# dlr_ut

**Source:** DLR Urban Traffic dataset (DLR-UT) v1.3.1,
https://zenodo.org/records/20919480 (downloaded 2026-07-20). License: CC BY-NC-SA 4.0.

**Real-data pedigree.** Multi-sensor infrastructure measurement at the AIM Research
Intersection and inner ring road, Braunschweig (2023-09-24, 12:00-13:00): 32,296 real
road-user trajectories incl. VRUs, published by DLR itself. The four OpenSCENARIO 1.2
files (one per 15-min slice) replay every recorded trajectory via
`FollowTrajectoryAction`; the referenced OpenDRIVE map is vendored under `map/`.

**Vendoring note.** The 4 `.xosc` (140-182 MB each) exceed GitHub's file limit; they
are git-ignored — run `../../fetch/fetch_dlr_ut.sh` to materialize
`scenarios/*.xosc` from Zenodo before benchmarking.

**Caveats for triage.** The scenarios reference vehicle/pedestrian catalogs
(`../xosc/Catalogs/...`) that the dataset does not ship — physcheck reports these as
info-severity SCH-007; entity envelopes are therefore unchecked. The declared
`LogicFile` path (`../xodr/...`) also does not match the zip layout, so the map is
passed explicitly via `CORPUS.json`.
