# dlr_ht

**Source:** DLR Highway Traffic dataset (DLR-HT) v1.2.0,
https://zenodo.org/records/18540070 (downloaded 2026-07-20). License: CC BY-NC-SA 4.0.

**Real-data pedigree.** Infrastructure-sensor measurement on Test Bed Lower Saxony
(motorways A2/A391/A39/L295 near Braunschweig, 2024-10-07): real trajectories with
weather and road-surface context, published by DLR. One OpenSCENARIO 1.2 file (1 min
of full highway traffic via `FollowTrajectoryAction`, 72 MB) + the OpenDRIVE map.

**Caveats for triage.** Same missing-catalog and LogicFile-path caveats as `dlr_ut`
(see its PROVENANCE.md); the map is passed via `CORPUS.json`.
