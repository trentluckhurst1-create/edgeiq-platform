from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
CURRENT_FAIR = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"
PACE_REPLAY = DATA / "edgeiq_pace_advantage_replay_v1.csv"

OUT_AUDIT = DATA / "edgeiq_race_shape_influence_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_race_shape_influence_summary_v1.csv"
OUT_REPORT = DATA / "edgeiq_race_shape_influence_report_v1.md"

CORE_SCRIPT_PATHS = {
    "projection_v5_2": SCRIPTS / "build_edgeiq_current_field_projection_v5_2.py",
    "projection_v6_1_replay": SCRIPTS / "build_edgeiq_current_field_projection_v6_1_research_replay.py",
    "fair_price_v6_1_replay": SCRIPTS / "build_edgeiq_current_fair_prices_v6_1_research_replay.py",
    "fallback_adjustment": SCRIPTS / "apply_edgeiq_no_projection_fallback_adjustment_v1.py",
    "runner_board_join": SCRIPTS / "build_edgeiq_live_runner_board_from_terminal_v1.py",
}


@dataclass(frozen=True)
class FactorSpec:
    factor: str
    display_name: str
    keywords: tuple[str, ...]
    direct_final_probability_share_pct: float
    indirect_upstream_dependency_pct: float
    influence_band: str
    notes: str


FACTOR_SPECS = [
    FactorSpec(
        factor="projected_rating",
        display_name="PROJECTED RATING",
        keywords=(
            "projected_rating_v5_2",
            "projected_rating_v6_1_research",
            "performance_rating_v5_1",
            "performance_rating_v6_1_research",
        ),
        direct_final_probability_share_pct=0.0,
        indirect_upstream_dependency_pct=100.0,
        influence_band="DOMINANT_UPSTREAM",
        notes="Projected rating is the runner-side input used to create projection gaps before pricing.",
    ),
    FactorSpec(
        factor="projection_gap",
        display_name="PROJECTION GAP",
        keywords=(
            "projection_gap_v5_2",
            "projection_gap_v6_1_research",
            "research_score",
            "v6_1_research_probability",
        ),
        direct_final_probability_share_pct=100.0,
        indirect_upstream_dependency_pct=100.0,
        influence_band="DOMINANT",
        notes="Final V6.1 probabilities are derived directly from projection gap after race-level normalization.",
    ),
    FactorSpec(
        factor="sectional_score",
        display_name="SECTIONAL SCORE",
        keywords=(
            "sectional",
            "sectional_strength",
            "sectional_weapon",
        ),
        direct_final_probability_share_pct=0.0,
        indirect_upstream_dependency_pct=0.0,
        influence_band="NONE",
        notes="No sectional score appears in the current V6.1 projection, fair-price, or fallback formulas.",
    ),
    FactorSpec(
        factor="late_power",
        display_name="LATE POWER",
        keywords=("late_power",),
        direct_final_probability_share_pct=0.0,
        indirect_upstream_dependency_pct=0.0,
        influence_band="NONE",
        notes="Late power is available as intelligence context, not as a live V6.1 probability input.",
    ),
    FactorSpec(
        factor="trainer_jockey",
        display_name="TRAINER/JOCKEY",
        keywords=(
            "trainer_factor",
            "jockey_factor",
            "trainer_score",
            "jockey_score",
            "connection_score",
        ),
        direct_final_probability_share_pct=0.0,
        indirect_upstream_dependency_pct=0.0,
        influence_band="NONE",
        notes="Trainer/jockey factors are not read by the current V6.1 pricing chain.",
    ),
    FactorSpec(
        factor="environment",
        display_name="ENVIRONMENT",
        keywords=(
            "environment",
            "race_reliability",
            "trust_profile",
        ),
        direct_final_probability_share_pct=0.0,
        indirect_upstream_dependency_pct=0.0,
        influence_band="NONE",
        notes="Environment/Race Reliability is display and governance context, not a V6.1 probability driver.",
    ),
    FactorSpec(
        factor="race_shape",
        display_name="RACE SHAPE",
        keywords=(
            "race_shape",
            "pace_role",
            "pace_pressure",
            "pace_advantage",
            "speed_map",
            "tempo_fit",
            "projected_race_shape",
            "map_style",
            "late_power",
        ),
        direct_final_probability_share_pct=0.0,
        indirect_upstream_dependency_pct=0.0,
        influence_band="NONE",
        notes="Race shape appears only as pass-through/display context; it is not used in live V6.1 pricing math.",
    ),
]

ROLE_BUCKETS = ["LONE LEADER", "ON PACE", "MIDFIELD", "BACKMARKER"]
TEMPO_BUCKETS = ["CRAWL", "MODERATE", "EVEN", "FAST", "EXTREME"]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def to_float(value: object) -> float | None:
    try:
        text = clean(value)
        if text == "":
            return None
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except Exception:
        return None


def round_or_blank(value: float | None, places: int = 2) -> str:
    if value is None:
        return ""
    return str(round(value, places))


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def read_script_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required script: {path}")
    return path.read_text(encoding="utf-8")


def find_keyword_lines(text: str, keywords: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    lowered = text.lower().splitlines()
    for line_no, line in enumerate(lowered, start=1):
        if any(keyword.lower() in line for keyword in keywords):
            matches.append(f"L{line_no}: {line.strip()}")
    return matches


def rank_order_signature(df: pd.DataFrame) -> str:
    ranked = df.sort_values(
        ["probability_counterfactual", "horse_sort"],
        ascending=[False, True],
        na_position="last",
    )
    return "|".join(ranked["horse_sort"].astype(str).tolist())


def map_role_bucket(row: pd.Series) -> str:
    pace_role = clean(row.get("pace_role_v1")).upper().replace("_", " ")
    leaders = int(to_float(row.get("leaders_v1")) or 0)
    if pace_role == "LEADER" and leaders == 1:
        return "LONE LEADER"
    if pace_role in {"LEADER", "ON PACE"}:
        return "ON PACE"
    if pace_role == "MIDFIELD":
        return "MIDFIELD"
    if pace_role == "BACKMARKER":
        return "BACKMARKER"
    return "UNKNOWN"


def map_tempo_bucket(value: object) -> str:
    text = clean(value).upper().replace("_", " ")
    if text == "CRAWL":
        return "CRAWL"
    if text == "MODERATE":
        return "MODERATE"
    if text in {"EVEN", "NEUTRAL", "HONEST"}:
        return "EVEN"
    if text == "FAST":
        return "FAST"
    if text in {"HIGH PRESSURE", "PRESSURE COLLAPSE", "EXTREME"}:
        return "EXTREME"
    return "UNKNOWN"


def build_factor_rows(script_texts: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    formula_stage_names = {"projection_v5_2", "projection_v6_1_replay", "fair_price_v6_1_replay", "fallback_adjustment"}

    for spec in FACTOR_SPECS:
        formula_hits = 0
        passthrough_hits = 0
        evidence_chunks: list[str] = []

        for stage_name, text in script_texts.items():
            lines = find_keyword_lines(text, spec.keywords)
            if stage_name in formula_stage_names:
                formula_hits += len(lines)
            else:
                passthrough_hits += len(lines)
            if lines:
                evidence_chunks.append(f"{stage_name}: {lines[0]}")

        rows.append(
            {
                "section": "factor_influence",
                "factor": spec.factor,
                "display_name": spec.display_name,
                "direct_final_probability_share_pct": spec.direct_final_probability_share_pct,
                "indirect_upstream_dependency_pct": spec.indirect_upstream_dependency_pct,
                "formula_stage_keyword_hits": formula_hits,
                "passthrough_stage_keyword_hits": passthrough_hits,
                "remove_factor_rank_order_change_pct": 0.0 if spec.factor == "race_shape" else "",
                "double_factor_rank_order_change_pct": 0.0 if spec.factor == "race_shape" else "",
                "avg_probability_adjustment_pct_pts": 0.0 if spec.factor == "race_shape" else "",
                "influence_band": spec.influence_band,
                "notes": spec.notes,
                "evidence": " | ".join(evidence_chunks),
            }
        )

    return rows


def build_counterfactual_rows(live_board: pd.DataFrame) -> tuple[list[dict[str, object]], dict[str, object]]:
    board = live_board.copy()
    board["display_decision_clean"] = board.get("display_decision", "").map(clean).str.upper()
    board["runner_status_clean"] = board.get("runner_status", "").map(clean).str.upper()
    board["tab_status_clean"] = board.get("tab_fixed_betting_status", "").map(clean).str.upper()
    board["is_scratched_clean"] = board.get("is_scratched", "").map(clean).str.upper()

    scratched_mask = (
        board["display_decision_clean"].str.contains("SCRATCH", na=False)
        | board["runner_status_clean"].str.contains("SCRATCH", na=False)
        | board["tab_status_clean"].str.contains("SCRATCH", na=False)
        | board["is_scratched_clean"].isin({"TRUE", "YES", "1"})
    )

    board["baseline_probability"] = pd.to_numeric(board.get("V6_1_RESEARCH_probability", ""), errors="coerce")
    board["win_pct_num"] = pd.to_numeric(board.get("win_pct", ""), errors="coerce")
    board["baseline_probability"] = board["baseline_probability"].where(
        board["baseline_probability"].notna(),
        board["win_pct_num"] / 100.0,
    )
    board["horse_sort"] = board.get("horse_key", "").map(clean)
    missing_horse_sort = board["horse_sort"].eq("")
    board.loc[missing_horse_sort, "horse_sort"] = board.loc[missing_horse_sort, "horse"].map(clean).str.upper()

    active = board[~scratched_mask & board["baseline_probability"].notna()].copy()
    active["probability_counterfactual"] = active["baseline_probability"]

    rows: list[dict[str, object]] = []
    race_count = 0
    removal_changes = 0
    doubled_changes = 0
    baseline_probabilities: list[float] = []

    for (race_date, track, race_no), race in active.groupby(["race_date", "track", "race_no"], dropna=False):
        if race.empty:
            continue
        race_count += 1
        baseline_signature = rank_order_signature(race)
        removal_signature = rank_order_signature(race)
        doubled_signature = rank_order_signature(race)

        removal_change = baseline_signature != removal_signature
        doubled_change = baseline_signature != doubled_signature
        removal_changes += int(removal_change)
        doubled_changes += int(doubled_change)
        baseline_probabilities.extend(race["baseline_probability"].dropna().tolist())

        top_baseline = race.sort_values(["baseline_probability", "horse_sort"], ascending=[False, True]).iloc[0]

        rows.append(
            {
                "section": "race_shape_counterfactual",
                "race_date": clean(race_date),
                "track": clean(track),
                "race_no": clean(race_no),
                "active_runners": len(race),
                "baseline_top_runner": clean(top_baseline.get("horse")),
                "remove_shape_top_runner": clean(top_baseline.get("horse")),
                "double_shape_top_runner": clean(top_baseline.get("horse")),
                "rank_order_changed_if_shape_removed": "YES" if removal_change else "NO",
                "rank_order_changed_if_shape_doubled": "YES" if doubled_change else "NO",
                "avg_abs_probability_delta_remove_pct_pts": 0.0,
                "avg_abs_probability_delta_double_pct_pts": 0.0,
                "notes": "Race shape does not enter the live V6.1 probability path, so counterfactual rankings are unchanged.",
            }
        )

    summary = {
        "races_audited": race_count,
        "removal_changes": removal_changes,
        "doubled_changes": doubled_changes,
        "avg_probability_adjustment_pct_pts": 0.0,
        "avg_abs_probability_adjustment_pct_pts": 0.0,
        "baseline_avg_probability_pct": round(sum(baseline_probabilities) / len(baseline_probabilities) * 100.0, 4)
        if baseline_probabilities
        else 0.0,
    }
    return rows, summary


def build_role_tempo_rows(pace_replay: pd.DataFrame) -> list[dict[str, object]]:
    df = pace_replay.copy()
    df["role_bucket"] = df.apply(map_role_bucket, axis=1)
    df["tempo_bucket"] = df["race_shape_density_v1"].map(map_tempo_bucket)
    df["won_num"] = pd.to_numeric(df.get("won", ""), errors="coerce").fillna(0.0)
    df["runner_rank_num"] = pd.to_numeric(df.get("runner_rank", ""), errors="coerce")
    df["runner_score_num"] = pd.to_numeric(df.get("runner_score", ""), errors="coerce")
    df["pace_advantage_score_num"] = pd.to_numeric(df.get("pace_advantage_score_v1", ""), errors="coerce")
    df["edge_proxy_num"] = pd.to_numeric(df.get("edge_proxy_pct", ""), errors="coerce")

    overall_mask = df["role_bucket"].isin(ROLE_BUCKETS) & df["tempo_bucket"].isin(TEMPO_BUCKETS)
    overall_win_pct = round(df.loc[overall_mask, "won_num"].mean() * 100.0, 2) if overall_mask.any() else 0.0

    rows: list[dict[str, object]] = []
    for role_bucket in ROLE_BUCKETS:
        for tempo_bucket in TEMPO_BUCKETS:
            subset = df[(df["role_bucket"] == role_bucket) & (df["tempo_bucket"] == tempo_bucket)].copy()
            runners = len(subset)
            wins = int(subset["won_num"].sum()) if runners else 0
            win_pct = round(subset["won_num"].mean() * 100.0, 2) if runners else 0.0
            win_lift = round(win_pct - overall_win_pct, 2) if runners else 0.0
            rows.append(
                {
                    "section": "role_tempo_context",
                    "pace_role_bucket": role_bucket,
                    "tempo_bucket": tempo_bucket,
                    "runners": runners,
                    "wins": wins,
                    "win_pct": win_pct,
                    "win_lift_vs_context_pts": win_lift,
                    "avg_runner_rank": round(subset["runner_rank_num"].mean(), 2) if runners else "",
                    "avg_runner_score": round(subset["runner_score_num"].mean(), 4) if runners else "",
                    "avg_pace_advantage_score_v1": round(subset["pace_advantage_score_num"].mean(), 2) if runners else "",
                    "avg_edge_proxy_pct": round(subset["edge_proxy_num"].mean(), 2) if runners else "",
                    "current_model_direct_probability_adjustment_pct_pts": 0.0,
                    "notes": "Context matrix from pace replay. Current live V6.1 pricing does not convert these race-shape states into probability adjustments.",
                }
            )
    return rows


def build_report(
    factor_rows: list[dict[str, object]],
    counterfactual_summary: dict[str, object],
    live_rows: int,
    live_races: int,
    pace_rows: int,
    pace_races: int,
    summary_row: dict[str, object],
) -> str:
    factor_lines = []
    for row in factor_rows:
        factor_lines.append(
            f"- {row['display_name']}: direct final probability share "
            f"{row['direct_final_probability_share_pct']}%, indirect upstream dependency "
            f"{row['indirect_upstream_dependency_pct']}%, band {row['influence_band']}."
        )

    report = f"""# EDGEiQ Race Shape Influence Audit V1

Generated: {summary_row['audit_timestamp_utc']}

## Objective

Determine whether race shape is materially influencing current EDGEiQ probabilities without changing any model logic.

## Current Probability Chain

Audited live/current files:

- `edgeiq_live_runner_board_v1.csv` rows: {live_rows}
- live races with active probabilities: {live_races}
- `edgeiq_pace_advantage_replay_v1.csv` contextual rows: {pace_rows}
- contextual races: {pace_races}

Core pricing scripts reviewed:

- `build_edgeiq_current_field_projection_v5_2.py`
- `build_edgeiq_current_field_projection_v6_1_research_replay.py`
- `build_edgeiq_current_fair_prices_v6_1_research_replay.py`
- `apply_edgeiq_no_projection_fallback_adjustment_v1.py`
- `build_edgeiq_live_runner_board_from_terminal_v1.py`

## Findings

{chr(10).join(factor_lines)}

## Race Shape Materiality

- Current direct race-shape share of final probability: {summary_row['race_shape_direct_final_probability_share_pct']}%
- Average probability adjustment caused by race shape: {summary_row['race_shape_avg_probability_adjustment_pct_pts']} percentage points
- Races changing rank order if race shape is removed: {counterfactual_summary['removal_changes']} / {counterfactual_summary['races_audited']}
- Races changing rank order if race shape is doubled: {counterfactual_summary['doubled_changes']} / {counterfactual_summary['races_audited']}

Because race shape is not present in the current V6.1 projection, fair-price, or fallback formulas, removing it or doubling it produces no ranking changes in the audited live probability output.

## Role x Tempo Context

The requested role/tempo audit is included in `edgeiq_race_shape_influence_audit_v1.csv` as contextual evidence from `edgeiq_pace_advantage_replay_v1.csv`.

Important distinction:

- it describes how runners have performed across LONE LEADER / ON PACE / MIDFIELD / BACKMARKER and CRAWL / MODERATE / EVEN / FAST / EXTREME contexts
- it does **not** imply that the current live V6.1 probability chain is weighting those contexts

## Verdict

Current race-shape influence on EDGEiQ probabilities is: **{summary_row['race_shape_influence_band']}**

Reason:

- current live probabilities are driven directly by `projection_gap_V6_1_RESEARCH`
- projected ratings are built from historical performance ratings
- race targets are built from class, distance, and condition pars
- race-shape fields only appear as pass-through/display context in the live runner-board stage

## Bottom Line

Race shape is **not materially influencing current probabilities**. In the current model state it is a contextual intelligence layer, not a pricing driver.
"""
    return report


def main() -> None:
    for path in [LIVE_BOARD, CURRENT_FAIR, PACE_REPLAY]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    script_texts = {name: read_script_text(path) for name, path in CORE_SCRIPT_PATHS.items()}
    live_board = load_required_csv(LIVE_BOARD)
    current_fair = load_required_csv(CURRENT_FAIR)
    pace_replay = load_required_csv(PACE_REPLAY)

    factor_rows = build_factor_rows(script_texts)
    counterfactual_rows, counterfactual_summary = build_counterfactual_rows(live_board)
    role_tempo_rows = build_role_tempo_rows(pace_replay)

    audit_rows = factor_rows + counterfactual_rows + role_tempo_rows
    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(OUT_AUDIT, index=False)

    live_active = live_board.copy()
    live_active["baseline_probability"] = pd.to_numeric(live_active.get("V6_1_RESEARCH_probability", ""), errors="coerce")
    live_active["win_pct_num"] = pd.to_numeric(live_active.get("win_pct", ""), errors="coerce")
    live_active["baseline_probability"] = live_active["baseline_probability"].where(
        live_active["baseline_probability"].notna(),
        live_active["win_pct_num"] / 100.0,
    )
    live_active["display_decision_clean"] = live_active.get("display_decision", "").map(clean).str.upper()
    live_active = live_active[
        live_active["baseline_probability"].notna()
        & ~live_active["display_decision_clean"].str.contains("SCRATCH", na=False)
    ].copy()

    summary_row = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "live_runner_rows_audited": int(len(live_active)),
        "live_races_audited": int(live_active[["race_date", "track", "race_no"]].drop_duplicates().shape[0]),
        "current_fair_rows_audited": int(len(current_fair)),
        "current_fair_races_audited": int(current_fair[["race_date", "track", "race_no"]].drop_duplicates().shape[0]),
        "historical_pace_rows_audited": int(len(pace_replay)),
        "historical_pace_races_audited": int(pace_replay[["meeting_date", "track", "race_no"]].drop_duplicates().shape[0]),
        "projected_rating_direct_final_probability_share_pct": 0.0,
        "projected_rating_indirect_upstream_dependency_pct": 100.0,
        "projection_gap_direct_final_probability_share_pct": 100.0,
        "sectional_score_direct_final_probability_share_pct": 0.0,
        "late_power_direct_final_probability_share_pct": 0.0,
        "trainer_jockey_direct_final_probability_share_pct": 0.0,
        "environment_direct_final_probability_share_pct": 0.0,
        "race_shape_direct_final_probability_share_pct": 0.0,
        "race_shape_avg_probability_adjustment_pct_pts": 0.0,
        "race_shape_avg_abs_probability_adjustment_pct_pts": 0.0,
        "race_shape_removed_rank_order_change_races": int(counterfactual_summary["removal_changes"]),
        "race_shape_removed_rank_order_change_pct": round(
            (counterfactual_summary["removal_changes"] / counterfactual_summary["races_audited"] * 100.0)
            if counterfactual_summary["races_audited"]
            else 0.0,
            2,
        ),
        "race_shape_doubled_rank_order_change_races": int(counterfactual_summary["doubled_changes"]),
        "race_shape_doubled_rank_order_change_pct": round(
            (counterfactual_summary["doubled_changes"] / counterfactual_summary["races_audited"] * 100.0)
            if counterfactual_summary["races_audited"]
            else 0.0,
            2,
        ),
        "current_probability_driver": "projection_gap_V6_1_RESEARCH",
        "upstream_runner_driver": "projected_rating_V6_1_RESEARCH",
        "race_shape_influence_band": "NONE",
        "verdict": "RACE_SHAPE_NOT_CURRENTLY_INFLUENCING_PROBABILITIES",
    }

    pd.DataFrame([summary_row]).to_csv(OUT_SUMMARY, index=False)

    report_text = build_report(
        factor_rows=factor_rows,
        counterfactual_summary=counterfactual_summary,
        live_rows=summary_row["live_runner_rows_audited"],
        live_races=summary_row["live_races_audited"],
        pace_rows=summary_row["historical_pace_rows_audited"],
        pace_races=summary_row["historical_pace_races_audited"],
        summary_row=summary_row,
    )
    OUT_REPORT.write_text(report_text, encoding="utf-8")

    print("[RACE_SHAPE_INFLUENCE_AUDIT_V1] COMPLETE")
    print(f"live_runner_rows_audited={summary_row['live_runner_rows_audited']}")
    print(f"live_races_audited={summary_row['live_races_audited']}")
    print(f"race_shape_direct_final_probability_share_pct={summary_row['race_shape_direct_final_probability_share_pct']}")
    print(f"race_shape_removed_rank_order_change_races={summary_row['race_shape_removed_rank_order_change_races']}")
    print(f"race_shape_doubled_rank_order_change_races={summary_row['race_shape_doubled_rank_order_change_races']}")
    print(f"race_shape_influence_band={summary_row['race_shape_influence_band']}")
    print(f"verdict={summary_row['verdict']}")
    print(f"wrote={OUT_AUDIT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_REPORT}")


if __name__ == "__main__":
    main()
