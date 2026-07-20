#!/usr/bin/env python3
"""Seeded-violation mutant generator for the physcheck benchmark.

Takes real-world OpenSCENARIO files (assumed physically plausible) and produces
mutants that each contain exactly ONE certainly-impossible physical violation.
A linter that misses a mutant's violation scores a false negative; the expected
rule family per mutation makes scoring strict (the right *kind* of rule must
fire, not just any rule).

Every mutation edits an element that already exists in the file (no synthetic
scaffolding is injected), so mutants stay as close to the real scenario as
possible. Which mutations apply to which file therefore depends on the file's
content; the applicability matrix is part of the output manifest.

Deterministic: no randomness — mutations are fixed value replacements.

Usage:
    python3 mutate.py corpora/<name> mutants/<name> [--manifest mutants/<name>/manifest.json]
"""

from __future__ import annotations

import argparse
import copy
import json
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Mutation:
    mid: str
    #: Rule-id prefixes, one of which must fire (error severity) to count as detected.
    expected_rules: tuple[str, ...]
    description: str
    #: Applies the mutation in place; returns True when it found a target.
    apply: Callable[[ET.ElementTree], bool]


def _set_first(tree: ET.ElementTree, xpath: str, attr: str, value: str) -> bool:
    elem = tree.getroot().find(xpath)
    if elem is None:
        return False
    elem.set(attr, value)
    return True


def _sun(tree: ET.ElementTree, attr: str, value: str) -> bool:
    return _set_first(tree, ".//Weather/Sun", attr, value)


def _weather(tree: ET.ElementTree, attr: str, value: str) -> bool:
    return _set_first(tree, ".//Weather", attr, value)


def _mutate_snow_hot(tree: ET.ElementTree) -> bool:
    weather = tree.getroot().find(".//Weather[Precipitation]")
    if weather is None:
        return False
    precip = weather.find("Precipitation")
    assert precip is not None
    precip.set("precipitationType", "snow")
    if precip.get("intensity") is not None:
        precip.set("intensity", "0.5")
    if precip.get("precipitationIntensity") is not None:
        precip.set("precipitationIntensity", "5.0")
    if weather.get("temperature") is None:
        return False  # cannot state the contradiction without a declared temperature
    weather.set("temperature", "303.15")  # +30 C snowfall
    return True


def _mutate_bbox_zero(tree: ET.ElementTree) -> bool:
    dims = tree.getroot().find(".//Vehicle/BoundingBox/Dimensions")
    if dims is None:
        return False
    dims.set("length", "0.0")
    dims.set("width", "0.0")
    dims.set("height", "0.0")
    return True


def _mutate_ped_speed(tree: ET.ElementTree) -> bool:
    # A pedestrian commanded to sprint at 15 m/s (world record ~ 12.4 m/s peak).
    root = tree.getroot()
    ped_names = {
        obj.get("name")
        for obj in root.findall(".//Entities/ScenarioObject")
        if obj.find("Pedestrian") is not None
    }
    if not ped_names:
        return False
    for private in root.findall(".//Init/Actions/Private"):
        if private.get("entityRef") in ped_names:
            target = private.find(".//AbsoluteTargetSpeed")
            if target is not None:
                target.set("value", "15.0")
                return True
    return False


def _mutate_vehicle_speed(tree: ET.ElementTree) -> bool:
    # Any absolute target speed -> 150 m/s (540 km/h; production-car impossible).
    target = tree.getroot().find(".//SpeedAction//AbsoluteTargetSpeed")
    if target is None:
        return False
    target.set("value", "150.0")
    return True


def _mutate_lane_change(tree: ET.ElementTree) -> bool:
    dyn = tree.getroot().find(".//LaneChangeAction/LaneChangeActionDynamics")
    if dyn is None or dyn.get("dynamicsDimension") != "time":
        return False
    dyn.set("value", "0.05")  # 50 ms lane change
    return True


def _mutate_world_offroad(tree: ET.ElementTree) -> bool:
    # Push the first Init teleport WorldPosition 2 km sideways: off any map.
    pos = tree.getroot().find(".//Init//TeleportAction/Position/WorldPosition")
    if pos is None or pos.get("y") is None:
        return False
    try:
        y = float(pos.get("y", ""))
    except ValueError:
        return False
    pos.set("y", str(y + 2000.0))
    return True


def _mutate_road_missing(tree: ET.ElementTree) -> bool:
    pos = tree.getroot().find(".//Init//TeleportAction/Position/LanePosition")
    if pos is None:
        pos = tree.getroot().find(".//Init//TeleportAction/Position/RoadPosition")
    if pos is None:
        return False
    pos.set("roadId", "999999")
    return True


def _mutate_entity_overlap(tree: ET.ElementTree) -> bool:
    # Teleport the second entity onto the first one's exact world position.
    positions = tree.getroot().findall(".//Init//TeleportAction/Position/WorldPosition")
    if len(positions) < 2:
        return False
    first, second = positions[0], positions[1]
    for attr in ("x", "y", "z", "h"):
        value = first.get(attr)
        if value is not None:
            second.set(attr, value)
        elif attr in ("x", "y") :
            return False
    return True


MUTATIONS: list[Mutation] = [
    Mutation("SUN_ELEV", ("SOL-001",), "sun elevation 2.0 rad (> zenith)",
             lambda t: _sun(t, "elevation", "2.0")),
    Mutation("SUN_AZIM", ("SOL-002",), "sun azimuth 7.0 rad (> 2*pi)",
             lambda t: _sun(t, "azimuth", "7.0")),
    Mutation("SUN_ILLUM", ("SOL-003",), "sun illuminance 200 klx (> solar constant)",
             lambda t: _sun(t, "illuminance", "200000")
             or _sun(t, "intensity", "200000")),
    Mutation("TEMP_HIGH", ("ATM-",), "air temperature 400 K",
             lambda t: _weather(t, "temperature", "400")),
    Mutation("PRESSURE_LOW", ("ATM-", "SCH-"), "atmospheric pressure 10 kPa at ground level",
             lambda t: _weather(t, "atmosphericPressure", "10000")),
    Mutation("SNOW_HOT", ("PRE-",), "snowfall at +30 C",
             _mutate_snow_hot),
    Mutation("FOG_NEG", ("SCH-", "ATM-"), "fog visual range -50 m",
             lambda t: _set_first(t, ".//Weather/Fog", "visualRange", "-50")),
    Mutation("WIND_EXTREME", ("PRE-",), "wind speed 150 m/s (> record gust)",
             lambda t: _set_first(t, ".//Weather/Wind", "speed", "150")),
    # SCH-112 (schema-range pack) is the canonical zero-bbox rule; ENT- category
    # envelopes also fire when the entity's category is declared.
    Mutation("BBOX_ZERO", ("ENT-", "SCH-112"), "vehicle bounding box 0x0x0 m",
             _mutate_bbox_zero),
    Mutation("MASS_TINY", ("ENT-",), "vehicle mass 1 kg",
             lambda t: _set_first(t, ".//Vehicle", "mass", "1")),
    Mutation("ACCEL_HUGE", ("KIN-",), "maxAcceleration 100 m/s^2 (~10 g)",
             lambda t: _set_first(t, ".//Vehicle/Performance", "maxAcceleration", "100")),
    Mutation("PED_SPRINT", ("KIN-",), "pedestrian commanded to 15 m/s",
             _mutate_ped_speed),
    Mutation("SPEED_150", ("KIN-",), "vehicle commanded to 150 m/s",
             _mutate_vehicle_speed),
    Mutation("LANE_50MS", ("KIN-",), "lane change completed in 50 ms",
             _mutate_lane_change),
    # L2 mutants (need the scenario's OpenDRIVE map at lint time):
    Mutation("OFFROAD_2KM", ("MAP-004",), "init spawn shifted 2 km off the map",
             _mutate_world_offroad),
    Mutation("ROAD_MISSING", ("MAP-001",), "init position references road 999999",
             _mutate_road_missing),
    Mutation("OVERLAP_INIT", ("MAP-005",), "two entities teleported to the same pose",
             _mutate_entity_overlap),
]


def mutate_corpus(src: Path, dst: Path, limit: int | None = None) -> dict[str, object]:
    dst.mkdir(parents=True, exist_ok=True)
    # Mirror OpenDRIVE maps so relative RoadNetwork/LogicFile paths keep resolving.
    for xodr in src.rglob("*.xodr"):
        target = dst / xodr.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(xodr.read_bytes())
    manifest: list[dict[str, object]] = []
    files = sorted(src.rglob("*.xosc"))
    if limit is not None:
        files = files[:limit]  # deterministic: first N in sorted order
    skipped = 0
    for path in files:
        try:
            base = ET.parse(path)
        except ET.ParseError:
            skipped += 1
            continue
        if base.getroot().find("Storyboard") is None:
            # Catalogs / distributions are not mutated, but mutants may reference
            # them (CatalogLocations) — mirror them verbatim.
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            skipped += 1
            continue
        for mutation in MUTATIONS:
            tree = copy.deepcopy(base)
            if not mutation.apply(tree):
                continue
            rel = path.relative_to(src)
            out = dst / rel.parent / f"{rel.stem}__{mutation.mid}.xosc"
            out.parent.mkdir(parents=True, exist_ok=True)
            tree.write(out, encoding="unicode", xml_declaration=True)
            manifest.append(
                {
                    "mutant": str(out.relative_to(dst)),
                    "source": str(rel),
                    "mutation": mutation.mid,
                    "expected_rules": list(mutation.expected_rules),
                    "description": mutation.description,
                }
            )
    return {
        "source_files": len(files),
        "skipped_unparseable_or_non_scenario": skipped,
        "mutants": manifest,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path, help="corpus directory with real .xosc files")
    ap.add_argument("dest", type=Path, help="output directory for mutants")
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=None,
                    help="mutate only the first N files (sorted; deterministic)")
    args = ap.parse_args()
    result = mutate_corpus(args.source, args.dest, limit=args.limit)
    manifest_path = args.manifest or args.dest / "manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{len(result['mutants'])} mutants from {result['source_files']} files "
          f"-> {args.dest} (manifest: {manifest_path})")


if __name__ == "__main__":
    main()
