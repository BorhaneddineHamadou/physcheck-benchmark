#!/usr/bin/env python3
"""physcheck benchmark runner: specificity on real corpora, sensitivity on mutants.

Ground truth model:
- Files in ``corpora/<name>/`` come from real recorded driving and are assumed
  physically plausible -> every error-clean file is a TRUE NEGATIVE; every
  error finding on them is a candidate FALSE POSITIVE (triaged by hand, see
  each corpus's PROVENANCE.md).
- Files in ``mutants/<name>/`` each carry ONE seeded, certainly-impossible
  violation (mutate.py) -> a mutant where a finding of the expected rule
  family fires is a TRUE POSITIVE; an unflagged mutant is a FALSE NEGATIVE.

Per corpus, an optional ``CORPUS.json`` configures the run:
    {"layers": "L0,L1,L2", "map": "relative/path.xodr", "provenance": "...",
     "osc_version": "1.0"}
Without it: layers L0,L1,L2 and per-scenario LogicFile map resolution.

Usage:
    python3 run_benchmark.py [--physcheck physcheck] [--corpus NAME ...]
Writes results/results_<toolversion>.json and results/table.md (the table is
what physcheck's README embeds).
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPORA = HERE / "corpora"
MUTANTS = HERE / "mutants"
RESULTS = HERE / "results"


def run_physcheck(binary: str, target: Path, layers: str, map_file: str | None) -> dict:
    cmd = [
        *shlex.split(binary), "lint", str(target),
        "--layers", layers,
        "--severity", "info",
        "--fail-on", "never",
        "--format", "json",
    ]
    if map_file:
        cmd += ["--map", map_file]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"physcheck failed ({proc.returncode}) on {target}:\n{proc.stderr[-2000:]}"
        )
    return json.loads(proc.stdout)


def tool_version(binary: str) -> str:
    out = subprocess.run([*shlex.split(binary), "--version"], capture_output=True, text=True, check=True)
    return out.stdout.strip().split()[-1]


def load_config(corpus_dir: Path) -> dict:
    config_path = corpus_dir / "CORPUS.json"
    config = {"layers": "L0,L1,L2", "map": None}
    if config_path.is_file():
        config.update(json.loads(config_path.read_text()))
    return config


def eval_real(report: dict, artifact_rules: tuple[str, ...] = ()) -> dict:
    """Specificity numbers over the real (assumed-plausible) corpus.

    The plausibility ground truth ("this happened, so it is physically
    possible") backs the PHYSICS layers (L1/L2). L0 findings judge the FILE's
    schema conformance — for machine-converted corpora those are converter
    defects, reported separately, never counted against physics specificity.

    ``artifact_rules`` are rule-id prefixes whose findings were manually
    triaged as TRUE findings about the conversion pipeline (template metadata,
    map under-coverage) rather than tool mistakes — justification is required
    in the corpus's CORPUS.json/PROVENANCE.md. They are excluded from the
    tool-false-positive count but fully reported under
    ``conversion_artifact_findings_by_rule``.
    """
    scenario_files = [
        f for f in report["files"] if f.get("document_kind", "scenario") == "scenario"
    ]
    fp_rules: dict[str, int] = {}
    l0_rules: dict[str, int] = {}
    warn_rules: dict[str, int] = {}
    files_with_physics_error = 0
    files_with_l0_error = 0
    files_with_warning = 0
    fp_details = []
    artifact_counts: dict[str, int] = {}
    files_with_artifact = 0
    files_with_tool_fp = 0
    for f in scenario_files:
        errors = [x for x in f.get("findings", []) if x["severity"] == "error"]
        physics = [x for x in errors if x["layer"] != "L0"]
        l0 = [x for x in errors if x["layer"] == "L0"]
        warnings = [x for x in f.get("findings", []) if x["severity"] == "warning"]
        artifacts = [x for x in physics if x["rule_id"].startswith(artifact_rules)] \
            if artifact_rules else []
        tool_fps = [x for x in physics if x not in artifacts]
        if artifacts:
            files_with_artifact += 1
            for x in artifacts:
                artifact_counts[x["rule_id"]] = artifact_counts.get(x["rule_id"], 0) + 1
        if physics:
            files_with_physics_error += 1
        if tool_fps:
            files_with_tool_fp += 1
            for x in tool_fps:
                fp_rules[x["rule_id"]] = fp_rules.get(x["rule_id"], 0) + 1
                fp_details.append({
                    "file": f["file"], "rule": x["rule_id"],
                    "message": x["message"][:200],
                })
        if l0:
            files_with_l0_error += 1
            for x in l0:
                l0_rules[x["rule_id"]] = l0_rules.get(x["rule_id"], 0) + 1
        if warnings:
            files_with_warning += 1
            for x in warnings:
                warn_rules[x["rule_id"]] = warn_rules.get(x["rule_id"], 0) + 1
    n = len(scenario_files)
    return {
        "scenario_files": n,
        "true_negatives": n - files_with_tool_fp,
        "files_with_physics_error": files_with_physics_error,
        "files_with_tool_fp": files_with_tool_fp,
        "specificity": round((n - files_with_tool_fp) / n, 4) if n else None,
        "files_with_conversion_artifact": files_with_artifact,
        "conversion_artifact_findings_by_rule": dict(sorted(artifact_counts.items())),
        "files_with_l0_error": files_with_l0_error,
        "l0_error_findings_by_rule": dict(sorted(l0_rules.items())),
        "files_with_warning": files_with_warning,
        "error_findings_by_rule": dict(sorted(fp_rules.items())),
        "warning_findings_by_rule": dict(sorted(warn_rules.items())),
        "candidate_false_positives": fp_details,
    }


def eval_mutants(report: dict, manifest: dict, mutants_dir: Path) -> dict:
    """Sensitivity numbers over the seeded-violation mutants."""
    findings_by_file: dict[str, list[dict]] = {}
    for f in report["files"]:
        findings_by_file[str(Path(f["file"]).resolve())] = f.get("findings", [])
    per_mutation: dict[str, dict[str, int]] = {}
    fn_details = []
    detected_any = detected_error = total = 0
    for entry in manifest["mutants"]:
        path = str((mutants_dir / entry["mutant"]).resolve())
        findings = findings_by_file.get(path, [])
        expected = tuple(entry["expected_rules"])
        hit_any = any(x["rule_id"].startswith(expected) for x in findings)
        hit_error = any(
            x["rule_id"].startswith(expected) and x["severity"] == "error"
            for x in findings
        )
        stats = per_mutation.setdefault(
            entry["mutation"], {"total": 0, "detected": 0, "detected_error": 0}
        )
        stats["total"] += 1
        total += 1
        if hit_any:
            stats["detected"] += 1
            detected_any += 1
        if hit_error:
            stats["detected_error"] += 1
            detected_error += 1
        if not hit_any:
            fn_details.append({
                "mutant": entry["mutant"], "mutation": entry["mutation"],
                "expected_rules": entry["expected_rules"],
                "rules_fired": sorted({x["rule_id"] for x in findings}),
            })
    return {
        "mutants": total,
        "detected": detected_any,
        "detected_error_severity": detected_error,
        "sensitivity": round(detected_any / total, 4) if total else None,
        "false_negatives": len(fn_details),
        "per_mutation": dict(sorted(per_mutation.items())),
        "false_negative_details": fn_details,
    }


def make_table(version: str, results: dict) -> str:
    lines = [
        "| Corpus (real data) | Files | Tool false positives | Specificity "
        "| Conversion-artifact findings¹ | Seeded mutants | Detected | Sensitivity |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, r in sorted(results.items()):
        real, mut = r["real"], r.get("mutants")
        mut_total = mut["mutants"] if mut else "—"
        mut_det = mut["detected"] if mut else "—"
        mut_sens = f"{mut['sensitivity']:.1%}" if mut and mut["sensitivity"] is not None else "—"
        artifact = real.get("files_with_conversion_artifact", 0)
        artifact_cell = f"{artifact} files" if artifact else "0"
        lines.append(
            f"| {name} | {real['scenario_files']} | {real['files_with_tool_fp']} "
            f"| {real['specificity']:.1%} | {artifact_cell} "
            f"| {mut_total} | {mut_det} | {mut_sens} |"
        )
    lines.append("")
    lines.append(
        "¹ Error findings manually verified as TRUE defects of the corpus's "
        "conversion pipeline (template metadata, converted-map under-coverage), "
        "not tool mistakes — triage evidence in the benchmark repo.")
    lines.append("")
    lines.append(f"*physcheck {version}; protocol, corpora provenance and per-finding "
                 "triage: see the [benchmark repo](https://github.com/BorhaneddineHamadou/physcheck-benchmark).*")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--physcheck", default="physcheck", help="physcheck executable")
    ap.add_argument("--corpus", action="append", help="only these corpora (default: all)")
    args = ap.parse_args()

    version = tool_version(args.physcheck)
    corpus_dirs = sorted(
        d for d in CORPORA.iterdir() if d.is_dir()
        and (args.corpus is None or d.name in args.corpus)
    )
    if not corpus_dirs:
        print("no corpora found under corpora/", file=sys.stderr)
        return 1

    all_results: dict[str, dict] = {}
    for corpus_dir in corpus_dirs:
        name = corpus_dir.name
        config = load_config(corpus_dir)
        map_file = (
            str(corpus_dir / config["map"]) if config.get("map") else None
        )
        print(f"[{name}] linting real corpus ...", flush=True)
        report = run_physcheck(args.physcheck, corpus_dir, config["layers"], map_file)
        artifact_rules = tuple(config.get("artifact_rules", []))
        entry: dict = {"config": config, "real": eval_real(report, artifact_rules)}

        mutants_dir = MUTANTS / name
        manifest_path = mutants_dir / "manifest.json"
        if manifest_path.is_file():
            print(f"[{name}] linting mutants ...", flush=True)
            mutant_map = (
                str(mutants_dir / config["map"]) if config.get("map") else map_file
            )
            mreport = run_physcheck(
                args.physcheck, mutants_dir, config["layers"], mutant_map
            )
            entry["mutants"] = eval_mutants(
                mreport, json.loads(manifest_path.read_text()), mutants_dir
            )
        all_results[name] = entry

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"results_{version}.json"
    out.write_text(json.dumps({"physcheck": version, "corpora": all_results}, indent=2),
                   encoding="utf-8")
    table = make_table(version, all_results)
    (RESULTS / "table.md").write_text(table + "\n", encoding="utf-8")
    print(f"\nwrote {out} and results/table.md\n")
    print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
