from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT = ROOT / "public" / "data" / "edgeiq_nexus_ui_v2_1_audit.csv"


def check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []

    rows.append(check(
        "calibrated_feed_referenced",
        "edgeiq_live_nexus_contextual_feed_v2_1.csv" in src,
        "V2.1 calibrated contextual feed is loaded by the Race Intelligence screen.",
    ))
    rows.append(check(
        "fallback_feed_preserved",
        "edgeiq_live_nexus_contextual_feed_v2.csv" in src and "nexusContextualFallback" in src,
        "V2 contextual feed remains as the fallback load source.",
    ))
    rows.append(check(
        "calibrated_score_fields_rendered",
        "nexus_context_score_calibrated" in src and "nexus_context_band_calibrated" in src,
        "Primary score card uses calibrated Nexus score and band fields.",
    ))
    rows.append(check(
        "race_rank_and_percentile_rendered",
        "nexus_context_rank_in_race" in src and "nexus_context_percentile" in src,
        "Race rank and percentile are available in the calibrated score card.",
    ))
    rows.append(check(
        "trainer_panel_rendered",
        "trainer_recent_25_win_pct" in src and "trainer_best_context" in src,
        "Trainer recent window and best-context fields are rendered.",
    ))
    rows.append(check(
        "jockey_panel_rendered",
        "jockey_recent_25_win_pct" in src and "jockey_best_context" in src,
        "Jockey recent window and best-context fields are rendered.",
    ))
    rows.append(check(
        "partnership_panel_rendered",
        "partnership_band" in src and "Partnership" in src,
        "Partnership panel is present and uses partnership band.",
    ))
    rows.append(check(
        "style_panel_rendered",
        "style_alignment_score" in src and "style_alignment_band" in src,
        "Style alignment panel is present.",
    ))
    raw_index = src.find("raw_nexus_context_score")
    primary_index = src.find("nexus_context_score_calibrated")
    rows.append(check(
        "raw_score_not_primary",
        primary_index >= 0 and raw_index >= 0 and primary_index < raw_index and "Raw context:" in src,
        "Raw Nexus context score is retained only as supporting context text.",
    ))
    rows.append(check(
        "sidecar_matcher_present",
        "findNexusContextualSidecar" in src and "nexusContextualRows" in src,
        "Calibrated contextual feed is joined to enriched runner rows.",
    ))
    rows.append(check(
        "compact_css_present",
        "edgeiq-nexus-v21-layout" in css and "edgeiq-nexus-score-card" in css,
        "V2.1 Nexus score layout classes are styled.",
    ))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    print(f"Nexus UI V2.1 audit: PASS={len(rows) - fail_count} FAIL={fail_count}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
