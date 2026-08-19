from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
ENRICHED = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v1.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_form_guide_v3_audit.txt"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_form_guide_v3_audit.json"

EXPECTED_SUMMARY_COLUMNS = [
    "NO",
    "SILK",
    "LAST 5",
    "HORSE",
    "TRAINER",
    "JOCKEY",
    "WT",
    "BAR",
    "DAYS",
    "EPI",
    "EARLY SPEED",
    "MARKET",
    "EDGEiQ PRICE",
    "SUITABILITY ENGINE",
    "SHAPE FIT",
    "LATE",
    "FORM MOMENTUM",
]

EXPECTED_RECENT_COLUMNS = [
    "DATE",
    "TRACK",
    "DIST",
    "COND",
    "POS",
    "MARGIN",
    "WT",
    "BAR",
    "SP",
    "RATING",
    "EPI",
    "800-600",
    "600-400",
    "400-200",
    "200-F",
    "EARLY SPEED",
    "SUITABILITY",
    "FORM MOMENTUM",
]

REMOVED_SUMMARY_COLUMNS = ["TRACK", "DIST", "COND", "CONFIDENCE", "SPEUP"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_columns(source: str, const_name: str) -> list[str]:
    match = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*\[(.*?)\];", source, re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def add_check(checks: list[dict], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})


def enriched_counts() -> dict[str, int]:
    if not ENRICHED.exists():
        return {}

    payload = json.loads(ENRICHED.read_text(encoding="utf-8"))
    races = payload.get("races", []) if isinstance(payload, dict) else []
    runners = [runner for race in races for runner in race.get("runners", [])]

    def has(value: object) -> bool:
        return value not in (None, "", [], {})

    return {
        "races": len(races),
        "runners": len(runners),
        "scratchings": sum(1 for runner in runners if runner.get("scratched")),
        "with_epi": sum(1 for runner in runners if has(runner.get("epi"))),
        "with_market": sum(1 for runner in runners if has(runner.get("marketPrice"))),
        "with_edgeiq_price": sum(1 for runner in runners if has(runner.get("edgeiqPrice"))),
        "with_full_form": sum(1 for runner in runners if has(runner.get("fullForm"))),
        "with_career_record": sum(1 for runner in runners if has(runner.get("careerRecord"))),
        "with_recent_form": sum(1 for runner in runners if has(runner.get("fullForm"))),
    }


def main() -> int:
    component = read(COMPONENT)
    normaliser = read(NORMALISER)
    workspace = read(WORKSPACE)
    css = read(CSS)
    checks: list[dict] = []

    summary_columns = extract_columns(component, "summaryColumns")
    recent_columns = extract_columns(component, "recentFormColumns")

    add_check(
        checks,
        "summary_columns_exact",
        summary_columns == EXPECTED_SUMMARY_COLUMNS,
        "Summary table columns match V3 contract.",
    )
    add_check(
        checks,
        "removed_columns_absent_from_summary",
        not any(column in summary_columns for column in REMOVED_SUMMARY_COLUMNS),
        "TRACK/DIST/COND/CONFIDENCE/SPEUP removed from summary table.",
    )
    add_check(
        checks,
        "recent_form_columns_exact",
        recent_columns == EXPECTED_RECENT_COLUMNS,
        "Recent Form columns match V3 contract and omit RACE.",
    )
    add_check(
        checks,
        "scratched_rows_non_selectable",
        "if (runner.scratched) return;" in component and "disabled={runner.scratched}" in component,
        "Scratched runners are disabled and cannot be selected.",
    )
    add_check(
        checks,
        "scratched_visual_treatment",
        ".eiq-form-summary-table--v3 tbody tr.is-scratched" in css
        and "text-decoration: line-through;" in css
        and "filter: grayscale(1)" in css,
        "Scratched rows are faded, darkened, muted and struck through.",
    )
    add_check(
        checks,
        "selected_runner_header_present",
        "eiq-form-v3-runner-header" in component and "SELECTED RUNNER" in component,
        "Selected runner profile header is rendered below the summary table.",
    )
    add_check(
        checks,
        "profile_sections_present",
        all(
            token in component
            for token in [
                "Career & Conditions Profile",
                "Track Condition",
                "Class Profile",
                "Jockey Profile",
                "Race-Day Pattern",
                "Last Start",
            ]
        ),
        "Full-width profile sections are present.",
    )
    add_check(
        checks,
        "key_insights_present",
        "EDGEiQ Key Insights" in component and "eiq-form-v3-insights" in component,
        "EDGEiQ Key Insights panel is present.",
    )
    add_check(
        checks,
        "recent_form_present",
        "Recent Form (Last 8 Starts)" in component and "eiq-form-run-table--v3" in component,
        "Recent Form section is present under the profile.",
    )
    add_check(
        checks,
        "sectional_fields_blank_contract",
        all(
            token in normaliser
            for token in [
                'esi800600: ""',
                'esi600400: ""',
                'esi400200: ""',
                'esi200F: ""',
            ]
        ),
        "Sectional columns are wired as blank-safe display fields only.",
    )
    add_check(
        checks,
        "unapproved_engine_fields_blank_contract",
        all(
            token in normaliser
            for token in [
                'earlySpeed: ""',
                'suitabilityScore: ""',
                'shapeFit: ""',
                'late: ""',
                'formMomentum: ""',
            ]
        ),
        "No Suitability/Momentum/Sectionals/Early Speed values are fabricated.",
    )
    add_check(
        checks,
        "workspace_tabs_preserved",
        all(token in workspace for token in ['"FORM GUIDE"', '"MARKET"', '"MAP"', '"OVERVIEW"']),
        "Existing workspace tabs are preserved.",
    )
    add_check(
        checks,
        "no_raw_json_dump",
        "JSON.stringify" not in component,
        "Form table does not render raw runner objects.",
    )
    add_check(
        checks,
        "no_stars",
        "★" not in component + normaliser and "☆" not in component + normaliser,
        "No star rating UI is present in the V3 form guide code.",
    )
    add_check(
        checks,
        "enriched_feed_available",
        ENRICHED.exists(),
        "Enriched form guide feed exists.",
    )

    counts = enriched_counts()
    status = "EDGEIQ_FORM_GUIDE_V3_AUDIT_PASS" if all(check["status"] == "PASS" for check in checks) else "EDGEIQ_FORM_GUIDE_V3_AUDIT_FAIL"
    result = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "counts": counts,
        "summary_columns": summary_columns,
        "recent_form_columns": recent_columns,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [status, f"Generated: {result['generated_at']}", ""]
    for check in checks:
        lines.append(f"{check['status']}: {check['name']} - {check['detail']}")
    lines.append("")
    lines.append("Counts:")
    for key, value in counts.items():
        lines.append(f"{key}: {value}")
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)
    print(f"Wrote {OUT_TXT}")
    print(f"Wrote {OUT_JSON}")
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
