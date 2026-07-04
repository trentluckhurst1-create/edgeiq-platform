from __future__ import annotations

import re
from collections import defaultdict

from edgeiq_results_common_v1 import DATA, ROOT, first, normalized_runner, normalize_race_no, now_iso, parse_date, race_key_for, read_csv, write_csv


OUT = DATA / "edgeiq_saddlecloth_order_audit_v1.csv"


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def number(row: dict[str, str]) -> int | None:
    raw = first(row, ["saddlecloth", "horse_no", "runner_no", "runner_number", "number", "tab_number"])
    try:
        return int(float(raw))
    except ValueError:
        return None


def race_key(row: dict[str, str]) -> str:
    return first(row, ["race_key"]) or race_key_for(parse_date(first(row, ["race_date", "meeting_date"])), first(row, ["track"]), normalize_race_no(first(row, ["race_no"])))


def audit_feed(name: str, rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = race_key(row)
        if key:
            grouped[key].append(row)
    out = []
    for key, group in grouped.items():
        nums = [number(row) for row in group]
        clean_nums = [value for value in nums if value is not None]
        in_order = clean_nums == sorted(clean_nums)
        duplicate_numbers = len(clean_nums) - len(set(clean_nums))
        out.append({
            "scope": "data_feed",
            "target": name,
            "race_key": key,
            "rows": len(group),
            "sequence": " ".join(str(value) for value in clean_nums[:30]),
            "missing_numbers": sum(1 for value in nums if value is None),
            "duplicate_numbers": duplicate_numbers,
            "status": "OK" if in_order and duplicate_numbers == 0 else "CHECK",
            "detail": "Saddlecloth order ascending" if in_order else "Feed row order is not saddlecloth ascending",
            "built_at": now_iso(),
        })
    return out


def audit_react() -> list[dict[str, object]]:
    component = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
    source = component.read_text(encoding="utf-8-sig")
    checks = [
        ("Race runner board", r"raceRunnerBoardRows\s*=\s*\[\.\.\.activeRaceRows\]\.sort\(\(a,\s*b\)\s*=>\s*saddle\(a\.row\)\s*-\s*saddle\(b\.row\)\)"),
        ("Field table", r"fieldRows\s*=\s*\[\.\.\.activeRaceRows\]\.sort\(\(a,\s*b\)\s*=>\s*saddle\(a\.row\)\s*-\s*saddle\(b\.row\)\)"),
        ("Form selector", r"formSelectorRows\s*=\s*\[\.\.\.activeRaceRows\]\.sort\(\(a,\s*b\)\s*=>\s*saddle\(a\.row\)\s*-\s*saddle\(b\.row\)\)"),
        ("Results official table", r"resultRows\s*=\s*\[\.\.\.activeRaceRows\]\.sort\(\(a,\s*b\)\s*=>\s*saddle\(a\.row\)\s*-\s*saddle\(b\.row\)\)"),
        ("Performance table", r"heatRows\s*=\s*activeRaceRows\.map"),
        ("Market table", r"marketRows\s*=\s*activeRaceRows"),
    ]
    return [{
        "scope": "react_table",
        "target": name,
        "race_key": "",
        "rows": "",
        "sequence": "",
        "missing_numbers": "",
        "duplicate_numbers": "",
        "status": "OK" if re.search(pattern, source) else "CHECK",
        "detail": "Saddlecloth ordered source confirmed" if re.search(pattern, source) else "Could not confirm saddlecloth ordered source",
        "built_at": now_iso(),
    } for name, pattern in checks]


def main() -> None:
    rows = []
    rows.extend(audit_feed("edgeiq_live_runner_board_governed_v1.csv", load("edgeiq_live_runner_board_governed_v1.csv")))
    rows.extend(audit_feed("edgeiq_vic_three_day_meeting_universe.csv", load("edgeiq_vic_three_day_meeting_universe.csv")))
    rows.extend(audit_react())
    fields = ["scope", "target", "race_key", "rows", "sequence", "missing_numbers", "duplicate_numbers", "status", "detail", "built_at"]
    write_csv(OUT, rows, fields)
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
