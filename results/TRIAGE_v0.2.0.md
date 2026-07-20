# Finding triage — physcheck 0.2.0

Every error-severity finding physcheck raised on the real corpora was triaged.
Verdict categories: **tool FP** (physcheck is wrong — counts against specificity),
**conversion artifact** (the finding is TRUE of the file, but the impossibility was
introduced by the dataset's conversion pipeline, not by the recorded reality),
**corpus defect** (true finding about the shipped files).

## corner_case_ndd, dlr_ut, dlr_ht

Zero error findings of any layer → nothing to triage. dlr_* additionally produce
info-severity SCH-007 (the datasets reference vehicle/pedestrian catalogs they do
not ship) — a true corpus observation, severity info, not counted anywhere.

## sctrans_real (all 1,079 files; verdicts verified on samples, mechanism identified)

| Rule(s) | Findings | Verdict | Evidence |
|---|---|---|---|
| SCH-001 (L0) | 1,079 | corpus defect | Every file's root element is `<OpenScenario>` — wrong case per the ASAM schema. Loads only in case-tolerant engines. (This defect also crashed physcheck ≤0.2.0's parser into skipping physics layers; fixed in the same release cycle — the benchmark's first catch.) |
| FRI-023, KIN-018 (L1) | 12,997 + 12,997 | conversion artifact | Every NPC vehicle declares `maxAcceleration = 200 m/s²` — CARLA's template placeholder stamped onto the real trajectories (same value as CARLA ScenarioRunner's own examples). |
| GEO-005 (L2) | 1,079 | conversion artifact | Every file declares sun elevation 75.1°, azimuth 0° (due north) — the same copy-pasted template environment as ScenarioRunner's examples; contradicts the ephemeris at the converted maps' declared origin under every timezone reading. |
| MAP-004 (L2) | 2,411 | conversion artifact | Verified sample (`DEU_AAH1-15_22`, Npc186 at (29.7, 48.2)): the point projects 10.6 m outside every lane of the converted `DEU_AAH1.xodr`. The CommonRoad→OpenDRIVE maps model only the roadway corridor, while inD's recording area includes vehicles on unmapped ground (parking, yards). Map under-coverage, not an impossible position in reality. |
| MAP-005 (L2) | 985 | conversion artifact | Verified sample (`DEU_AAH1-11_126`, Npc181 vs Npc190): "Npc190" is a **pedestrian declared with a 5.0 × 2.0 m bounding box** — a car-size template stamped on a person. The real 2.4 m separation becomes a phantom bbox overlap. (The absurd pedestrian dims are themselves flagged by ENT-010/011 warnings.) |
| PRE-012 (L1) | 557 | conversion artifact | Template weather declares rain together with a cloud-free sky. |

**Tool false positives after triage: 0.** The `artifact_rules` list in
`corpora/sctrans_real/CORPUS.json` encodes this triage; `run_benchmark.py` excludes
those rule ids from the tool-FP count while still reporting them in full under
`conversion_artifact_findings_by_rule`.

Note the epistemics: the artifact findings are *correct linter behavior* — the files
really do declare impossible physics, which is precisely what a plausibility linter
must surface about a machine-converted suite. They are excluded only from the
"tool is wrong" metric, not from the results.

## Mutant scoring notes

- `BBOX_ZERO` is detected by SCH-112 ("Bounding box with non-positive dimensions",
  schema-range pack) and, where the entity's category allows envelope checks, by
  ENT- rules. The expected-family list includes both since v0.2.0 scoring;
  an earlier draft expected only ENT- and undercounted (corner_case_ndd 0/25
  despite every mutant being flagged by SCH-112).
- dlr_ut / dlr_ht are specificity-only corpora (no mutants): their scenario files
  are 72–182 MB trajectory replays; mutating them would dominate runtime for no
  added coverage of rule families.
