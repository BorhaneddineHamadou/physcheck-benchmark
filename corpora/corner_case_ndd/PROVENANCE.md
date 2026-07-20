# corner_case_ndd

**Source:** "Corner-Case Dataset for Autonomous Vehicle Testing Based on Naturalistic
Driving Data" (Jilin University; Smart Cities 8(4):129, 2025,
https://doi.org/10.3390/smartcities8040129). Figshare:
https://doi.org/10.6084/m9.figshare.28888034.v1 (downloaded 2026-07-20). License: CC BY 4.0.

**Real-data pedigree.** Corner cases extracted from (a) ~78 km instrumented-vehicle
naturalistic driving in Changchun, (b) ~10 h drone recordings (Yatai Street
Expressway) plus highD, (c) real dashcam accident videos (CCD/A3D). Scenarios were
reconstructed and exported to OpenSCENARIO 1.1 + OpenDRIVE with MathWorks RoadRunner
(R2024a); each of the 25 category directories holds one `scenario.xosc` +
`scenario.xodr` pair. Only the OpenX pair is vendored here (videos/osgb dropped).

**Caveats for triage.** RoadRunner is the export tool; findings may reflect export
defaults (e.g. environment templates) rather than the recorded reality.
