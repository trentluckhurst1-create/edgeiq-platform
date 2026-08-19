from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"

AUDIT_TXT = DATA / "edgeiq_form_guide_rebuild_v1_audit.txt"
AUDIT_JSON = DATA / "edgeiq_form_guide_rebuild_v1_audit.json"

EXPECTED_COLUMNS = [
    "NO",
    "SILK",
    "LAST 5",
    "HORSE",
    "TRAINER",
    "JOCKEY",
    "WT",
    "BAR",
    "EPI",
    "TRACK",
    "DIST",
    "COND",
]

PROHIBITED_COLUMNS = [
    "career record",
    "dry record",
    "wet record",
    "total prize money",
    "prize money",
    "api",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def source_check(name: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }


def walk_runners(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    runners: list[dict[str, Any]] = []

    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            for runner in race.get("runners", []):
                runners.append(
                    {
                        "meeting": meeting.get("meeting"),
                        "date": meeting.get("date"),
                        "race": race.get("raceNumber"),
                        "official": runner.get("official") or {},
                    }
                )

    return runners


def main() -> int:
    component = read(COMPONENT)
    normaliser = read(NORMALISER)
    race_workspace = read(RACE_WORKSPACE)
    race_file = read(RACE_FILE)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}
    runners = walk_runners(catalog)

    column_match = re.search(r"const summaryColumns = \[(.*?)\];", component, re.S)
    columns = re.findall(r'"([^"]+)"', column_match.group(1)) if column_match else []
    raw_names = [
        runner
        for runner in runners
        if str(runner["official"].get("runner") or "").strip().startswith(("{", "["))
        or "[object Object]" in str(runner["official"].get("runner") or "")
    ]
    last_five_over_cap = [
        runner
        for runner in runners
        if len(runner["official"].get("lastFive") or []) > 5
    ]

    checks = [
        source_check("form guide component exists", COMPONENT.exists(), str(COMPONENT)),
        source_check("normaliser exists", NORMALISER.exists(), str(NORMALISER)),
        source_check("RaceWorkspace uses RaceFormGuideWorkspace", "RaceFormGuideWorkspace" in race_workspace),
        source_check("RaceFileV3 passes meeting race selector props", "meetingRaces=" in race_file and "onOpenRace=" in race_file),
        source_check("summary columns exact order", columns == EXPECTED_COLUMNS, "|".join(columns)),
        source_check(
            "prohibited PuntingForm columns absent",
            not any(item in component.lower() for item in PROHIBITED_COLUMNS),
        ),
        source_check("silks rendered as image", "<img" in component and "silkUrl" in component),
        source_check("last five capped", "slice(0, 5)" in normaliser),
        source_check("runner selection scrolls to detail", "scrollIntoView" in component),
        source_check("full form detail block exists", "FULL FORM" in component and "eiq-form-runner-detail" in component),
        source_check("unsafe eval absent", re.search(r"\beval\s*\(", normaliser + component + race_workspace) is None),
        source_check("catalog exists", CATALOG.exists(), str(CATALOG)),
        source_check("catalog runner rows available", len(runners) > 0, str(len(runners))),
        source_check("catalog raw object runner names absent", not raw_names, str(raw_names[:3])),
        source_check("catalog last five capped", not last_five_over_cap, str(last_five_over_cap[:3])),
        source_check(
            "catalog silks available where source provides them",
            any((runner["official"].get("silkUrl") or "") for runner in runners),
        ),
    ]

    passed = all(check["status"] == "PASS" for check in checks)
    status = "EDGEIQ_FORM_GUIDE_REBUILD_V1_AUDIT_PASS" if passed else "EDGEIQ_FORM_GUIDE_REBUILD_V1_AUDIT_FAIL"
    payload = {
      "status": status,
      "generated_at": datetime.now().isoformat(),
      "runner_rows_checked": len(runners),
      "checks": checks,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    AUDIT_TXT.write_text(
        "\n".join(
            [
                status,
                f"generated_at={payload['generated_at']}",
                f"runner_rows_checked={len(runners)}",
                "",
                *[
                    f"{check['status']} | {check['check']} | {check['details']}"
                    for check in checks
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(status)
    print(f"runner_rows_checked={len(runners)}")
    print(f"audit_txt={AUDIT_TXT}")
    print(f"audit_json={AUDIT_JSON}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
