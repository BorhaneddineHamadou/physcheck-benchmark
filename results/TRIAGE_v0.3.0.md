# Triage — physcheck 0.3.0 (L3 kinematic feasibility)

The first 0.3.0 run (L3 newly enabled on all corpora) surfaced three new finding
classes on real data plus 4 mutant false negatives. Each was investigated to the
underlying mechanism before deciding tool-fix vs. conversion-artifact. Two were
tool defects (fixed in physcheck before release), one is a verified export
artifact (classified in `CORPUS.json`), and the FNs were mutation-operator
defects (fixed in `mutate.py`).

## 1. DYN-001 ×69 on sctrans_real (57 files) — TOOL DEFECT, fixed

Messages claimed curve radii of 4–9 m under vehicles commanded to 10–13 m/s.
Verified on `DEU_AAH1-10_37_T-1.xosc` / `DEU_AAH1.xodr`: road `2` is a genuine
12.5 m corner-arc road (paramPoly3, κ≈0.18 at s=11) of the converted inD
intersection — but `Npc188` spawns via **WorldPosition** and physcheck
*projected* it onto the nearest reference line. At junctions, short corner-arc
roads overlap the through path, so projection routinely assigns a
straight-through vehicle to a curved road it never drives.

**Fix (physcheck, D32):** DYN-001 now runs only for declared RoadPosition/
LanePosition spawns; world positions are never projected onto a road for the
curve-speed check. The file's own roadId claim is the only claim v² > µgr can
safely refute.

## 2. DYN-006 ×14 on corner_case_ndd (6 files) — TOOL DEFECT, fixed

Multiple vehicles flagged with the *same* 62.8 m/s² "sustained" acceleration.
Verified on `Free driving→Highway+Normal behavior+Sunny`, vehicle3 vertices
64–73: the export samples at 25 Hz with positions quantised to a 0.1 m grid, so
adjacent-sample speeds alternate 37.5 ↔ 40.0 m/s (dist 1.5/1.6 m per 0.04 s) —
pure rounding, differentiated into ±62.5 m/s² of phantom acceleration on every
sample (which also defeated the consecutive-violation guard, since the noise
alternates).

**Fix (physcheck, D31):** DYN-006 estimates speed/acceleration over ≥0.4 s
windows on each side of a vertex (path/elapsed-time, curvature from window
endpoints). Quantisation error drops to ~1 m/s²; sustained real braking (the
TRAJ_BRAKE_WALL mutant, 25 m/s² for 1.6 s) is still detected. Regression test:
`test_dyn006_immune_to_position_quantisation`.

## 3. DYN-005 ×1 on corner_case_ndd — EXPORT ARTIFACT, classified

`Free driving→Urban road+Rare behavior+Night`, vehicle3: first vertex at
(3.0, 0.0), second at (3.0, 11.0) 40 ms later — an 11 m jump (274 m/s), after
which the track continues smoothly at 37.5 m/s. The RoadRunner export wrote a
placeholder first frame before the actor's real track start. Physically
impossible as declared → correct linter output about a true defect of the
export pipeline, not a tool mistake. Added `DYN-005` to
`corpora/corner_case_ndd/CORPUS.json` `artifact_rules`.

## 4. Mutant false negatives ×4 — OPERATOR DEFECTS, fixed

- `TRAJ_BRAKE_WALL` (2 FN): the operator wrote a 40→15→0 m/s *step* profile
  onto the file's existing timestamps; with sparse vertex spacing the step
  landed inside a single estimation window and never produced two consecutive
  violating vertices. Now writes a *continuous* profile (cruise 1 s at 40 m/s,
  then 25 m/s² to a stop) and requires ≥2 vertices inside the braking phase.
- `TRAJ_PED_SPRINT` (2 FN): fixed ×8 scaling of a slow walk (~0.3 m/s) stayed
  under the 6 m/s sustained ceiling. Now scales adaptively to an 8 m/s average
  over the span (skips near-stationary tracks, requires ≥12 s span).

## Coverage note

DYN-001 (curve speed) and DYN-002 (lane-change lateral acceleration) have no
mutation operator: no corpus offers a deterministic curved-road spawn or a
time-dimension LaneChangeAction (LANE_50MS/LANE_105 found zero targets in every
corpus). Both are covered by physcheck unit tests (synthetic arc map); DYN-002
additionally passed a 51-lane-change false-positive scan on esmini
(`docs/first_findings.md`, Update 4). Reported here so the gap is explicit
rather than silent.

## 5. Second-pass findings (after fixes 1-4)

- **DYN-006 ×13 on dlr_ut (4 files) — DATASET DEFECT, classified.** The windowed
  estimator (fix 2) surfaced what raw differencing had masked as single-sample
  spikes: replayed speeds that step instantaneously. Verified on entity
  `1695556999843816` (12:00 slice), v69→v70: 11.4 → 18.4 m/s within one 0.05 s
  sample (~140 m/s²), smooth motion on both sides — a track re-association in
  the DLR tracking pipeline. Physically impossible as declared → correct linter
  output about a true dataset defect. `DYN-006` added to
  `corpora/dlr_ut/CORPUS.json` artifact_rules. (dlr_ht, same pipeline family,
  shows none — its motorway tracks do not overlap/re-associate.)
- **DYN-006 ×1 on corner_case_ndd — TOOL DEFECT, fixed.** The already-classified
  placeholder-first-frame jump (finding 3) leaked into estimation windows that
  straddled it, re-reporting the same defect as 90.8 m/s² of "sustained"
  acceleration. Fixed in physcheck (D33): teleport-grade segments are data
  breaks — DYN-005 owns the jump, and DYN-006/DYN-007 analyse the runs on
  either side separately. Regression test:
  `test_teleport_is_a_data_break_not_phantom_acceleration`.

## 6. Third-pass finding

- **DYN-006 ×1 on corner_case_ndd — RECONSTRUCTION DEFECT, classified.** Same
  file as finding 3 (`Urban road+Rare behavior+Night`, vehicle3), but a second,
  independent mechanism beyond the (now break-split) first-frame jump: the
  track then decelerates 37.2 → 0 m/s in ~0.6 s as a clean exponential decay
  (speed ×~0.895 per 40 ms sample, τ≈0.36 s) — 6-9 g sustained with no
  crash-pulse shape, i.e. an easing/smoothing filter stopping the actor, not
  vehicle dynamics (real tire-limited braking is ≤~1.1 g; crash pulses last
  ~0.1 s, not 0.6 s). Correct linter output about the reconstruction. `DYN-006`
  added to `corpora/corner_case_ndd/CORPUS.json` artifact_rules. Note the
  order of operations: the DYN-006 *tool* defect (finding 2, quantisation) was
  fixed in physcheck FIRST — only the residual, mechanism-verified finding is
  classified as a corpus artifact, so the artifact rule does not mask tool
  regressions that the mutants would not catch.
