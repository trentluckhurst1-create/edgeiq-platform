from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
DATA_DIR = ROOT / "public" / "data"

RACE_INTEL_PATH = SRC_DIR / "components" / "RaceIntelligenceScreen.tsx"
MARKET_TAB_PATH = SRC_DIR / "terminal" / "tabs" / "MarketTab.tsx"
METRIC_RECOMMENDATIONS_PATH = DATA_DIR / "edgeiq_metric_display_recommendations_v1.csv"

INVENTORY_PATH = DATA_DIR / "edgeiq_intelligence_ui_content_inventory_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_intelligence_ui_content_inventory_v1_summary.csv"
HIERARCHY_PATH = DATA_DIR / "edgeiq_intelligence_screen_hierarchy_recommendation_v1.csv"
REFACTOR_PLAN_PATH = DATA_DIR / "edgeiq_intelligence_ui_refactor_plan_v1.csv"


@dataclass(frozen=True)
class BlockSpec:
    block_name: str
    file_path: Path
    start_marker: str
    visible_labels: str
    data_fields_used: str
    duplicated_with: str
    recommended_tier: str
    keep_promote_demote_hide: str
    reason: str


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def find_line_number(lines: list[str], marker: str) -> int:
    for index, line in enumerate(lines, start=1):
        if marker in line:
            return index
    return -1


def tier_sort_value(value: str) -> int:
    order = {
        "TIER_1_DECISION": 1,
        "TIER_2_EXPLANATION": 2,
        "TIER_3_RESEARCH": 3,
        "HIDE_OR_DRAWER": 4,
    }
    return order.get(value, 99)


def main() -> int:
    built_at = datetime.now().astimezone().isoformat(timespec="seconds")

    race_lines = read_lines(RACE_INTEL_PATH)
    market_lines = read_lines(MARKET_TAB_PATH)
    file_lines = {
        str(RACE_INTEL_PATH): race_lines,
        str(MARKET_TAB_PATH): market_lines,
    }

    metric_recommendations = pd.DataFrame()
    if METRIC_RECOMMENDATIONS_PATH.exists():
        metric_recommendations = pd.read_csv(METRIC_RECOMMENDATIONS_PATH, dtype=str, keep_default_na=False)

    blocks = [
        BlockSpec(
            "Race Header",
            RACE_INTEL_PATH,
            "const titleMeta = [",
            "race identity; date; class; distance; track condition; rail; meeting status",
            "currentMeeting; currentRace; race_date; track; race_no; race_class; distance; track_condition; rail_position",
            "Meeting preview header in Overview; Market selected race banner",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This is the orientation anchor for every race-day decision and should stay visible with stronger priority than any explanation panel.",
        ),
        BlockSpec(
            "Race Briefing",
            RACE_INTEL_PATH,
            "<span style={narrativeHeaderTextStyle}>Race Briefing</span>",
            "Race Briefing; Race Shape",
            "briefingRows; race_clarity; expected_tempo; top_win_chance; best_value; fair_price; edge_pct",
            "Race Verdict; Market Intelligence; Selected Runner reason",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This answers the race-level story in plain language, but currently overlaps with verdict and selected-runner narrative.",
        ),
        BlockSpec(
            "Market Intelligence",
            RACE_INTEL_PATH,
            "<span style={narrativeHeaderTextStyle}>Market Intelligence</span>",
            "Market Intelligence; Market Read",
            "marketIntelRows; live_price; market_state; edge_pct; best_value; value_edge",
            "Price Edge; MarketTab market story; Decision Board live/fair/edge columns",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "Value and market status are central race-day questions, but the copy should stay concise because the selected runner and board already carry numeric detail.",
        ),
        BlockSpec(
            "Race Verdict",
            RACE_INTEL_PATH,
            "<span style={narrativeHeaderTextStyle}>Race Verdict</span>",
            "Race Verdict; EDGEiQ Call",
            "verdictRows; final_call; confidence; top_win_chance; best_value",
            "Final Call card; Decision Board final call column",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "The race-level call is useful, but it should sit closer to the main decision summary and not compete equally with every other supporting block.",
        ),
        BlockSpec(
            "Track Intelligence",
            RACE_INTEL_PATH,
            "<span style={narrativeHeaderTextStyle}>Track Intelligence</span>",
            "Track Intelligence; Historical DNA",
            "trackIntelRows; track_dna_style; track_dna_barrier; best_track_fit_score; track_intelligence_comment",
            "Runner Profile; Track fit details in drawer; MarketTab contextual notes",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "Helpful context, but not the first thing a race-day user needs once the main win/value/confidence answers are known.",
        ),
        BlockSpec(
            "Selected Runner",
            RACE_INTEL_PATH,
            "Selected Runner</span>",
            "Selected Runner; win chance; fair price; TAB price; value edge; EDGEiQ confidence; final call",
            "selected row: horse; win_pct; fair_price; live_price; edge_pct; display_grade; final_call",
            "Decision Board selected row; Price Edge; Final Call card",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This is the best place to answer WHO / VALUE / SHOULD I BET for the focused runner, so it should become the main decision panel rather than one panel among many.",
        ),
        BlockSpec(
            "EDGEiQ Decision Breakdown",
            RACE_INTEL_PATH,
            "<span>EDGEiQ Decision Breakdown</span>",
            "EDGEiQ Decision Breakdown",
            "selected runner sub-panels: price edge; runner profile; DNA; performance factors; data quality; final call",
            "Race Briefing; Market Intelligence; Factor Scorecard; Final Call card",
            "TIER_2_EXPLANATION",
            "KEEP_RESTRUCTURE",
            "This is the right home for explanation, but it currently contains both critical decision cues and deep research content without enough separation.",
        ),
        BlockSpec(
            "Price Edge",
            RACE_INTEL_PATH,
            "<span>Price Edge</span>",
            "Price Edge",
            "selected fair_price; live_price; edge_pct; display_bet",
            "Decision Board value columns; Market Intelligence",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This is one of the most actionable blocks and should sit higher than DNA / Data Quality / Factor Scorecard content.",
        ),
        BlockSpec(
            "Runner Profile",
            RACE_INTEL_PATH,
            "<span>Runner Profile</span>",
            "Runner Profile; Projection Gap; Rating Status",
            "projection_band_V6_1_RESEARCH; projection_gap_V6_1_RESEARCH; V6_1_RESEARCH_price_status",
            "Selected Runner strip; Decision Board rank/win/fair context",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "Projection context explains the runner, but it is a support layer after the main price/value/confidence call.",
        ),
        BlockSpec(
            "Runner DNA",
            RACE_INTEL_PATH,
            "<span>RUNNER DNA</span>",
            "Runner DNA; DNA Score; Race Rank; Top Positives; Top Risks",
            "runnerDnaDrawer; dna_v6_2_score; dna_v6_2_band; positive/negative factors; dna_rank",
            "Performance Factors; DNA Explanation; DNA Factor Scorecard",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "DNA is strong supporting context, but the current treatment is too large for default race-day scanning and should collapse into a cleaner explanation zone.",
        ),
        BlockSpec(
            "DNA Explanation",
            RACE_INTEL_PATH,
            "EDGEiQ DNA Explanation",
            "EDGEiQ DNA Explanation",
            "selectedDnaNarrative",
            "Runner DNA summary; Race Briefing narrative",
            "TIER_3_RESEARCH",
            "DEMOTE_COLLAPSE",
            "This is useful as an on-demand explainer, but it competes with more important decision copy when always fully expanded.",
        ),
        BlockSpec(
            "Factor Scorecard",
            RACE_INTEL_PATH,
            "DNA Factor Scorecard",
            "DNA Factor Scorecard",
            "factorRows; factor_score; factor_band; strongest / weakest factor flags",
            "Runner DNA top positives/risks; Data Quality; research-level factor panels",
            "HIDE_OR_DRAWER",
            "DEMOTE_DRAWER",
            "High-detail factor bars are useful for advanced users, but they are too granular for the default decision surface.",
        ),
        BlockSpec(
            "Performance Factors",
            RACE_INTEL_PATH,
            "<span>Performance Factors</span>",
            "Performance Factors; Projected SPD; Sectional Weapon; Late Power",
            "projected_spd; sectional_weapon_score; late_power_index",
            "Runner DNA; Track Intelligence; Data Quality",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "These are genuine support signals, but they should be grouped as explanation rather than presented as a peer to the final call.",
        ),
        BlockSpec(
            "Data Quality",
            RACE_INTEL_PATH,
            "<span>Data Quality</span>",
            "Data Quality; Confidence Score; EDGEiQ Confidence; Bet Quality",
            "limited score; display grade; bet quality; confidence source; coverage text",
            "Selected Runner strip; Final Call; Decision Board confidence column",
            "TIER_3_RESEARCH",
            "DEMOTE_COLLAPSE",
            "The screen needs confidence, but the detailed data-quality block should sit lower because it repeats score/grade signals already exposed elsewhere.",
        ),
        BlockSpec(
            "Final Call",
            RACE_INTEL_PATH,
            "<span>Final Call</span>",
            "Final Call; Price Signal; Model View",
            "current decision; display bet; limited decision; final call narrative",
            "Race Verdict; Selected Runner strip; Decision Board final call",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This should be near the top of the selected-runner area as the explicit answer to SHOULD I BET, with less duplication around it.",
        ),
        BlockSpec(
            "Decision Board",
            RACE_INTEL_PATH,
            "<span>Decision Board</span>",
            "#; Runner; Barrier; Jockey; Win Chance; Fair Price; TAB Price; Value Edge; EDGEiQ Confidence; Final Call",
            "runner board rows; live/fair/edge; display grade; final call",
            "Selected Runner strip; MarketTab price board",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This is the core scan table and should remain the main comparison surface, with the selected-runner block acting as the deep focus view above it.",
        ),
        BlockSpec(
            "MarketTab Header",
            MARKET_TAB_PATH,
            "<span>EDGEiQ MARKET INTELLIGENCE</span>",
            "EDGEiQ Market Intelligence; selected race; market story; market confidence",
            "selectedMeetingKey; selectedRaceKey; rows; market status pills",
            "Race Intelligence Market Intelligence block",
            "TIER_1_DECISION",
            "KEEP_REFOCUS",
            "The Market tab should stay price-centric, but its header should support the same top-level questions instead of duplicating pending-state prose.",
        ),
        BlockSpec(
            "Market Story",
            MARKET_TAB_PATH,
            "<div className=\"edgeiq-mini-note-label\">Market Story</div>",
            "Market Story",
            "story; personality; favourite; support/drift counts",
            "Race Briefing; Race-level Market Intelligence block",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "Useful context, but it is explanation rather than the main decision payload once the race header and price board are visible.",
        ),
        BlockSpec(
            "Market Movers",
            MARKET_TAB_PATH,
            "<div className=\"edgeiq-panel-title\">MARKET MOVERS</div>",
            "Market Movers; Market Leader; Strongest Firmer; Largest Drifter; Stable Runners",
            "favourite; strongestFirm; strongestDrift; stable count",
            "TAB Price Board",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "This is supportive context that can sit below the top market summary rather than feeling like a second hero section.",
        ),
        BlockSpec(
            "Market Picture",
            MARKET_TAB_PATH,
            "<div className=\"edgeiq-panel-title\">MARKET PICTURE</div>",
            "Market Picture; TAB Read; Market State; TAB Coverage; Market Depth; Movement Count",
            "marketConfidence; marketStatusTone; overround; firmers; drifters; pricedRows",
            "Race Intelligence market cards; top market summary cards",
            "TIER_2_EXPLANATION",
            "KEEP_DEMOTE",
            "Good context, but it should read as secondary explanation under the main price board rather than a co-equal headline section.",
        ),
        BlockSpec(
            "TAB Price Board",
            MARKET_TAB_PATH,
            "<div className=\"edgeiq-panel-title\">TAB PRICE BOARD</div>",
            "#; Runner; Barrier; Opening Price; TAB Price; Move; Market View",
            "rows; barrier; live/open prices; move; market view",
            "Decision Board live/fair/edge columns",
            "TIER_1_DECISION",
            "KEEP_PROMOTE",
            "This is the primary actionable table in Market and should stay visible as the core scan surface.",
        ),
    ]

    records: list[dict[str, object]] = []
    blocks_by_file: dict[str, list[dict[str, object]]] = {}

    for spec in blocks:
        file_key = str(spec.file_path)
        lines = file_lines[file_key]
        start_line = find_line_number(lines, spec.start_marker)
        blocks_by_file.setdefault(file_key, []).append(
            {
                "block_name": spec.block_name,
                "file": spec.file_path.name,
                "component_path": str(spec.file_path.relative_to(ROOT)),
                "start_line": start_line,
                "end_line": -1,
                "visible_labels": spec.visible_labels,
                "data_fields_used": spec.data_fields_used,
                "duplicated_with": spec.duplicated_with,
                "recommended_tier": spec.recommended_tier,
                "keep_promote_demote_hide": spec.keep_promote_demote_hide,
                "reason": spec.reason,
            }
        )

    for file_key, block_rows in blocks_by_file.items():
        sorted_rows = sorted(block_rows, key=lambda row: row["start_line"] if row["start_line"] != -1 else 99999)
        file_length = len(file_lines[file_key])
        for index, row in enumerate(sorted_rows):
            if row["start_line"] == -1:
                row["end_line"] = -1
                continue
            next_start = next(
                (candidate["start_line"] for candidate in sorted_rows[index + 1 :] if candidate["start_line"] != -1),
                file_length,
            )
            row["end_line"] = max(row["start_line"], next_start - 1)
            row["approximate_line_range"] = f"{row['start_line']}-{row['end_line']}"
            records.append(row)

    inventory_df = pd.DataFrame(records)
    inventory_df.insert(0, "built_at", built_at)
    inventory_df = inventory_df.sort_values(
        by=["component_path", "start_line"],
        key=lambda series: series,
    ).reset_index(drop=True)
    inventory_df.to_csv(INVENTORY_PATH, index=False, encoding="utf-8")

    tier_counts = inventory_df["recommended_tier"].value_counts().to_dict()
    action_counts = inventory_df["keep_promote_demote_hide"].value_counts().to_dict()
    duplicated_blocks = inventory_df[inventory_df["duplicated_with"].astype(str).str.strip().ne("")]

    summary_rows = [
        {"metric": "built_at", "value": built_at},
        {"metric": "blocks_audited", "value": int(len(inventory_df))},
        {"metric": "tier_1_decision_blocks", "value": tier_counts.get("TIER_1_DECISION", 0)},
        {"metric": "tier_2_explanation_blocks", "value": tier_counts.get("TIER_2_EXPLANATION", 0)},
        {"metric": "tier_3_research_blocks", "value": tier_counts.get("TIER_3_RESEARCH", 0)},
        {"metric": "hide_or_drawer_blocks", "value": tier_counts.get("HIDE_OR_DRAWER", 0)},
        {"metric": "keep_promote_blocks", "value": action_counts.get("KEEP_PROMOTE", 0)},
        {"metric": "keep_demote_blocks", "value": action_counts.get("KEEP_DEMOTE", 0)},
        {"metric": "demote_collapse_blocks", "value": action_counts.get("DEMOTE_COLLAPSE", 0)},
        {"metric": "demote_drawer_blocks", "value": action_counts.get("DEMOTE_DRAWER", 0)},
        {
            "metric": "main_duplication_cluster",
            "value": "Race Briefing / Market Intelligence / Race Verdict / Selected Runner / Final Call all overlap on win/value/call language.",
        },
        {
            "metric": "primary_recommendation",
            "value": "Promote Who Wins / Best Value / Final Call / Confidence into the top strip and board. Demote DNA, data quality, and factor scorecards into explanation/drawer layers.",
        },
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY_PATH, index=False, encoding="utf-8")

    hierarchy_rows = [
        {
            "screen_zone": "TOP_STRIP",
            "purpose": "Answer WHO WINS / WHERE IS VALUE / SHOULD I BET / HOW CONFIDENT ARE WE at a glance",
            "blocks_to_feature": "Race Header|Top Win Chance|Best Value|Best Call|EDGEiQ Confidence|Market Status",
            "blocks_to_demote_from_here": "Track Intelligence|DNA Explanation|Factor Scorecard|Data Quality detail",
            "recommended_tier": "TIER_1_DECISION",
            "notes": "This should become the race-day orientation and decision strip before any long narrative.",
        },
        {
            "screen_zone": "MAIN_DECISION_BOARD",
            "purpose": "Fast runner-by-runner comparison",
            "blocks_to_feature": "Decision Board",
            "blocks_to_demote_from_here": "Deep factor rows; duplicated explanation copy",
            "recommended_tier": "TIER_1_DECISION",
            "notes": "Keep the board compact: runner, win chance, fair, TAB, edge, confidence, final call.",
        },
        {
            "screen_zone": "SELECTED_RUNNER_DECISION",
            "purpose": "Focused answer for the chosen runner",
            "blocks_to_feature": "Selected Runner|Price Edge|Final Call|Reason sentence|Confidence",
            "blocks_to_demote_from_here": "DNA factor scorecard; verbose data-quality text",
            "recommended_tier": "TIER_1_DECISION",
            "notes": "Make this the main WHY block after the table, with critical decision cues first and explanation second.",
        },
        {
            "screen_zone": "EXPLANATION_PANEL",
            "purpose": "Explain the call without overwhelming the first screen",
            "blocks_to_feature": "Runner Profile|Runner DNA|Performance Factors|Track Intelligence",
            "blocks_to_demote_from_here": "Raw factor bars; repeated prose already covered in top strip",
            "recommended_tier": "TIER_2_EXPLANATION",
            "notes": "These are supporting reasons, not first-order decision objects.",
        },
        {
            "screen_zone": "ADVANCED_DRAWER",
            "purpose": "Hold research and audit detail for power users",
            "blocks_to_feature": "Data Quality|DNA Explanation|Factor Scorecard|historical profile text",
            "blocks_to_demote_from_here": "Primary decision surface",
            "recommended_tier": "HIDE_OR_DRAWER",
            "notes": "Important, but too detailed for the default race-day screen.",
        },
        {
            "screen_zone": "MARKET_TAB_ROLE",
            "purpose": "Keep Market price-centric and complementary to Intelligence",
            "blocks_to_feature": "TAB Price Board|Market Leader|Market Story short form",
            "blocks_to_demote_from_here": "Long preview prose; duplicated final-call language",
            "recommended_tier": "TIER_1_DECISION",
            "notes": "Market should answer how the TAB book is shaping, not re-tell the full intelligence story.",
        },
    ]
    pd.DataFrame(hierarchy_rows).to_csv(HIERARCHY_PATH, index=False, encoding="utf-8")

    plan_rows = [
        {
            "sequence": 1,
            "files_to_edit": "src/components/RaceIntelligenceScreen.tsx",
            "blocks_to_move": "Race Briefing|Market Intelligence|Race Verdict",
            "target_zone": "TOP_STRIP",
            "action": "compress and promote",
            "risk_level": "LOW",
            "reason": "These blocks already answer the main race-day questions but currently compete as equal-weight cards.",
            "do_not_touch": "model calculations; fair-price values; selection logic",
        },
        {
            "sequence": 2,
            "files_to_edit": "src/components/RaceIntelligenceScreen.tsx",
            "blocks_to_move": "Selected Runner|Price Edge|Final Call",
            "target_zone": "SELECTED_RUNNER_DECISION",
            "action": "consolidate into one primary decision panel",
            "risk_level": "LOW",
            "reason": "This reduces duplication between selected-runner strip, final call, and top-level narrative.",
            "do_not_touch": "decision values; runner joins; confidence calculations",
        },
        {
            "sequence": 3,
            "files_to_edit": "src/components/RaceIntelligenceScreen.tsx",
            "blocks_to_move": "Runner Profile|Runner DNA|Performance Factors|Track Intelligence",
            "target_zone": "EXPLANATION_PANEL",
            "action": "group and visually subordinate",
            "risk_level": "MEDIUM",
            "reason": "Explanation content should remain visible, but after the main decision surface.",
            "do_not_touch": "DNA feed wiring; track-intelligence feed wiring",
        },
        {
            "sequence": 4,
            "files_to_edit": "src/components/RaceIntelligenceScreen.tsx",
            "blocks_to_move": "Data Quality|DNA Explanation|Factor Scorecard",
            "target_zone": "ADVANCED_DRAWER",
            "action": "collapse or drawerise",
            "risk_level": "MEDIUM",
            "reason": "These are the highest-noise blocks relative to immediate race-day value.",
            "do_not_touch": "underlying values; labels that feed other components",
        },
        {
            "sequence": 5,
            "files_to_edit": "src/terminal/tabs/MarketTab.tsx",
            "blocks_to_move": "Market Story|Market Movers|Market Picture",
            "target_zone": "MARKET_TAB_ROLE",
            "action": "reduce duplication and tighten hierarchy",
            "risk_level": "LOW",
            "reason": "Market should reinforce price state, not repeat the full intelligence narrative.",
            "do_not_touch": "price polling; future-meeting pending logic; market table data",
        },
        {
            "sequence": 6,
            "files_to_edit": "src/components/RaceIntelligenceScreen.tsx|src/terminal/tabs/MarketTab.tsx",
            "blocks_to_move": "labels only",
            "target_zone": "global",
            "action": "rename and simplify customer-facing copy",
            "risk_level": "LOW",
            "reason": "This is the safest cleanup if we want a first pass before any structural move.",
            "do_not_touch": "JS logic branches; fetch wiring; current refresh pipeline",
        },
    ]
    pd.DataFrame(plan_rows).to_csv(REFACTOR_PLAN_PATH, index=False, encoding="utf-8")

    print("[EDGEIQ_INTELLIGENCE_UI_CONTENT_INVENTORY_V1] COMPLETE")
    print(f"blocks_audited={len(inventory_df)}")
    print(f"tier_1_decision_blocks={tier_counts.get('TIER_1_DECISION', 0)}")
    print(f"tier_2_explanation_blocks={tier_counts.get('TIER_2_EXPLANATION', 0)}")
    print(f"tier_3_research_blocks={tier_counts.get('TIER_3_RESEARCH', 0)}")
    print(f"hide_or_drawer_blocks={tier_counts.get('HIDE_OR_DRAWER', 0)}")
    print(f"wrote={INVENTORY_PATH}")
    print(f"wrote={SUMMARY_PATH}")
    print(f"wrote={HIERARCHY_PATH}")
    print(f"wrote={REFACTOR_PLAN_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"[EDGEIQ_INTELLIGENCE_UI_CONTENT_INVENTORY_V1] FAILED: {exc}", file=sys.stderr)
        raise
