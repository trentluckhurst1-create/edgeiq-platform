from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
PROFILE = DATA / "edgeiq_sectional_features_v30_1_live_join_audit.csv"
MANIFEST_30_1 = DATA / "edgeiq_sectional_features_v30_1_manifest.json"

OUT = DATA / "edgeiq_live_runner_board_sectionals_v31.csv"
OUT_AUDIT = DATA / "edgeiq_live_runner_board_sectionals_v31_audit.csv"
OUT_SUMMARY = DATA / "edgeiq_live_runner_board_sectionals_v31_summary.csv"
OUT_MANIFEST = DATA / "edgeiq_live_runner_board_sectionals_v31_manifest.json"

SECTIONAL_FIELDS = [
    "sectional_history_runs",
    "sectional_history_status",
    "sectional_history_quality",
    "sectional_weapon_score",
    "sectional_weapon_band",
    "sectional_late_power_score",
    "sectional_late_power_band",
    "sectional_early_speed_score",
    "sectional_early_speed_band",
    "sectional_consistency_score",
    "sectional_consistency_band",
    "sectional_trajectory_score",
    "sectional_trajectory_band",
    "sectional_trajectory_delta",
    "sectional_feature_source",
    "sectional_feature_version",
]

PROTECTED_COLUMNS = [
    "race_date", "day_bucket", "track", "race_no", "race_key", "meeting_key", "runner_key",
    "horse", "horse_key", "horse_no", "saddlecloth", "barrier", "jockey", "trainer",
    "distance", "race_class", "live_price", "tab_fixed_win", "tab_fixed_place",
    "projected_rating_v5_2", "projection_gap_v5_2", "projection_band_v5_2", "projection_confidence_v5_2",
    "projected_rating_V6_1_RESEARCH", "projection_gap_V6_1_RESEARCH", "projection_band_V6_1_RESEARCH",
    "V6_1_RESEARCH_probability", "V6_1_RESEARCH_fair_price", "V6_1_RESEARCH_price_status",
    "V6_1_RESEARCH_price_bucket", "V6_1_RESEARCH_price_rank", "win_pct", "fair_price", "rated_price",
    "ui_fair_price", "edge_pct", "ui_edge_pct", "execution_action", "display_source", "display_decision",
    "display_edge_pct", "display_live_price", "display_fair_price", "is_scratched", "scratch_status",
    "runner_status", "execution_action_final",
]


def n(v: object) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else np.nan
    except Exception:
        return np.nan


def same_series(a: pd.Series, b: pd.Series) -> bool:
    aa = a.fillna("<NA>").astype(str)
    bb = b.fillna("<NA>").astype(str)
    return bool(aa.equals(bb))


def quality(runs: int, has_score: bool) -> str:
    if runs >= 3 and has_score:
        return "STRONG_HISTORY"
    if runs >= 2 and has_score:
        return "MODERATE_HISTORY"
    if runs >= 1 and has_score:
        return "LIMITED_HISTORY"
    return "NO_HISTORY"


def main() -> None:
    for p in [LIVE, PROFILE, MANIFEST_30_1]:
        if not p.exists():
            raise FileNotFoundError(p)

    m30 = json.loads(MANIFEST_30_1.read_text(encoding="utf-8"))
    if not bool(m30.get("ready_for_live_runner_board_join", False)):
        raise RuntimeError("V30.1 is not certified ready for live runner board join")

    live = pd.read_csv(LIVE, low_memory=False)
    prof = pd.read_csv(PROFILE, low_memory=False)

    before = live.copy(deep=True)
    input_rows = len(live)
    if "live_row" not in prof.columns:
        raise RuntimeError("V30.1 profile missing live_row")

    prof["live_row"] = pd.to_numeric(prof["live_row"], errors="coerce").astype("Int64")
    invalid_live_rows = int((prof["live_row"].isna() | (prof["live_row"] < 0) | (prof["live_row"] >= input_rows)).sum())
    duplicate_profile_live_rows = int(prof["live_row"].dropna().duplicated().sum())
    if invalid_live_rows or duplicate_profile_live_rows:
        raise RuntimeError(
            f"Unsafe V30.1 profile mapping: invalid_live_rows={invalid_live_rows} duplicate_profile_live_rows={duplicate_profile_live_rows}"
        )

    # Initialize sidecar fields. Existing live-board columns are never overwritten.
    for c in SECTIONAL_FIELDS:
        if c in live.columns:
            raise RuntimeError(f"Refusing to overwrite existing live-board column: {c}")
        live[c] = np.nan

    audit_rows: list[dict[str, object]] = []
    for _, p in prof.iterrows():
        i = int(p["live_row"])
        runs = int(n(p.get("prior_sectional_runs"))) if not pd.isna(n(p.get("prior_sectional_runs"))) else 0
        weapon = n(p.get("sectional_weapon_score"))
        late = n(p.get("late_power_score"))
        early = n(p.get("historical_early_speed_score"))
        consistency = n(p.get("sectional_consistency_score"))
        trajectory = n(p.get("sectional_trajectory_score"))
        delta = n(p.get("sectional_trajectory_delta"))
        any_score = any(not pd.isna(x) for x in [weapon, late, early, consistency, trajectory])

        vals = {
            "sectional_history_runs": runs,
            "sectional_history_status": "HAS_HISTORY" if runs > 0 else "NO_HISTORY",
            "sectional_history_quality": quality(runs, any_score),
            "sectional_weapon_score": weapon,
            "sectional_weapon_band": p.get("sectional_weapon_band", "LIMITED_DATA") if runs > 0 else "LIMITED_DATA",
            "sectional_late_power_score": late,
            "sectional_late_power_band": p.get("late_power_band", "LIMITED_DATA") if runs > 0 else "LIMITED_DATA",
            "sectional_early_speed_score": early,
            "sectional_early_speed_band": p.get("historical_early_speed_band", "LIMITED_DATA") if runs > 0 else "LIMITED_DATA",
            "sectional_consistency_score": consistency,
            "sectional_consistency_band": p.get("sectional_consistency_band", "LIMITED_DATA") if runs > 0 else "LIMITED_DATA",
            "sectional_trajectory_score": trajectory,
            "sectional_trajectory_band": p.get("sectional_trajectory_band", "LIMITED_DATA") if runs > 0 else "LIMITED_DATA",
            "sectional_trajectory_delta": delta,
            "sectional_feature_source": "V29_GOVERNED_VIA_V30_1_STRICT_PRIOR" if runs > 0 else "NO_SECTIONAL_HISTORY",
            "sectional_feature_version": "V31",
        }
        for c, v in vals.items():
            live.at[i, c] = v

        audit_rows.append({
            "live_row": i,
            "runner_key": before.at[i, "runner_key"] if "runner_key" in before.columns else "",
            "race_date": before.at[i, "race_date"] if "race_date" in before.columns else "",
            "track": before.at[i, "track"] if "track" in before.columns else "",
            "race_no": before.at[i, "race_no"] if "race_no" in before.columns else "",
            "horse": before.at[i, "horse"] if "horse" in before.columns else "",
            "horse_key": before.at[i, "horse_key"] if "horse_key" in before.columns else "",
            "sectional_history_runs": runs,
            "sectional_history_status": vals["sectional_history_status"],
            "sectional_history_quality": vals["sectional_history_quality"],
            "sectional_weapon_score": weapon,
            "sectional_late_power_score": late,
            "sectional_early_speed_score": early,
            "sectional_consistency_score": consistency,
            "sectional_trajectory_score": trajectory,
        })

    audit = pd.DataFrame(audit_rows).sort_values("live_row", kind="mergesort")

    # Hard safety audits: sidecar build must not mutate the original board.
    output_rows = len(live)
    row_count_delta = output_rows - input_rows
    protected_changed_columns: list[str] = []
    for c in PROTECTED_COLUMNS:
        if c in before.columns and c in live.columns and not same_series(before[c], live[c]):
            protected_changed_columns.append(c)

    pricing_decision_changed_columns = [c for c in protected_changed_columns if any(k in c.lower() for k in [
        "price", "probability", "fair", "edge", "decision", "action", "projection", "rating"
    ])]

    scratch_changed_columns = [c for c in ["is_scratched", "scratch_status", "runner_status"] if c in protected_changed_columns]
    runner_key_duplicates_before = int(before["runner_key"].duplicated().sum()) if "runner_key" in before.columns else 0
    runner_key_duplicates_after = int(live["runner_key"].duplicated().sum()) if "runner_key" in live.columns else 0

    history_runs = pd.to_numeric(live["sectional_history_runs"], errors="coerce").fillna(0)
    matched = int((history_runs >= 1).sum())
    unmatched = int((history_runs == 0).sum())
    with_weapon = int(pd.to_numeric(live["sectional_weapon_score"], errors="coerce").notna().sum())
    with_late = int(pd.to_numeric(live["sectional_late_power_score"], errors="coerce").notna().sum())
    with_early = int(pd.to_numeric(live["sectional_early_speed_score"], errors="coerce").notna().sum())
    with_consistency = int(pd.to_numeric(live["sectional_consistency_score"], errors="coerce").notna().sum())
    with_trajectory = int(pd.to_numeric(live["sectional_trajectory_score"], errors="coerce").notna().sum())

    score_range_errors = 0
    for c in [
        "sectional_weapon_score", "sectional_late_power_score", "sectional_early_speed_score",
        "sectional_consistency_score", "sectional_trajectory_score"
    ]:
        s = pd.to_numeric(live[c], errors="coerce")
        score_range_errors += int(((s < 0) | (s > 100)).fillna(False).sum())

    # Leakage assurance inherits V30.1's explicit strict cutoff audit.
    strict_prior_leakage = int(m30.get("live_date_leakage", 0))

    ready = (
        bool(m30.get("ready_for_live_runner_board_join", False))
        and row_count_delta == 0
        and not protected_changed_columns
        and runner_key_duplicates_after == runner_key_duplicates_before
        and score_range_errors == 0
        and strict_prior_leakage == 0
        and invalid_live_rows == 0
        and duplicate_profile_live_rows == 0
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    live.to_csv(OUT, index=False)
    audit.to_csv(OUT_AUDIT, index=False)

    summary_rows = [
        {"metric": "input_rows", "value": input_rows},
        {"metric": "output_rows", "value": output_rows},
        {"metric": "row_count_delta", "value": row_count_delta},
        {"metric": "matched_sectional_history", "value": matched},
        {"metric": "unmatched_sectional_history", "value": unmatched},
        {"metric": "with_sectional_weapon", "value": with_weapon},
        {"metric": "with_late_power", "value": with_late},
        {"metric": "with_early_speed", "value": with_early},
        {"metric": "with_consistency", "value": with_consistency},
        {"metric": "with_trajectory", "value": with_trajectory},
        {"metric": "runner_key_duplicates_before", "value": runner_key_duplicates_before},
        {"metric": "runner_key_duplicates_after", "value": runner_key_duplicates_after},
        {"metric": "protected_columns_changed", "value": len(protected_changed_columns)},
        {"metric": "pricing_decision_columns_changed", "value": len(pricing_decision_changed_columns)},
        {"metric": "scratch_columns_changed", "value": len(scratch_changed_columns)},
        {"metric": "score_range_errors", "value": score_range_errors},
        {"metric": "strict_prior_leakage", "value": strict_prior_leakage},
        {"metric": "invalid_live_rows", "value": invalid_live_rows},
        {"metric": "duplicate_profile_live_rows", "value": duplicate_profile_live_rows},
    ]
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

    manifest = {
        "build_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_live_board": str(LIVE.relative_to(ROOT)),
        "source_sectional_profile": str(PROFILE.relative_to(ROOT)),
        "source_v30_1_manifest": str(MANIFEST_30_1.relative_to(ROOT)),
        "output": str(OUT.relative_to(ROOT)),
        "input_rows": input_rows,
        "output_rows": output_rows,
        "row_count_delta": row_count_delta,
        "matched_sectional_history": matched,
        "unmatched_sectional_history": unmatched,
        "with_sectional_weapon": with_weapon,
        "with_late_power": with_late,
        "with_early_speed": with_early,
        "with_consistency": with_consistency,
        "with_trajectory": with_trajectory,
        "protected_columns_changed": protected_changed_columns,
        "pricing_decision_columns_changed": pricing_decision_changed_columns,
        "scratch_columns_changed": scratch_changed_columns,
        "runner_key_duplicates_before": runner_key_duplicates_before,
        "runner_key_duplicates_after": runner_key_duplicates_after,
        "score_range_errors": score_range_errors,
        "strict_prior_leakage": strict_prior_leakage,
        "ready_for_intelligence_ui": bool(ready),
        "policy": "SUPPLEMENTARY_SECTIONAL_EVIDENCE_ONLY_NO_PRICING_OR_DECISION_MUTATION",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("V31 LIVE RUNNER BOARD SECTIONAL SIDECAR JOIN")
    print()
    print("SOURCE")
    print(f"input_rows={input_rows}")
    print(f"v30_1_ready={m30.get('ready_for_live_runner_board_join', False)}")
    print()
    print("JOIN")
    print(f"output_rows={output_rows}")
    print(f"row_count_delta={row_count_delta}")
    print(f"matched_sectional_history={matched}")
    print(f"unmatched_sectional_history={unmatched}")
    print(f"with_sectional_weapon={with_weapon}")
    print(f"with_late_power={with_late}")
    print(f"with_early_speed={with_early}")
    print(f"with_consistency={with_consistency}")
    print(f"with_trajectory={with_trajectory}")
    print()
    print("PRESERVATION")
    print(f"runner_key_duplicates_before={runner_key_duplicates_before}")
    print(f"runner_key_duplicates_after={runner_key_duplicates_after}")
    print(f"protected_columns_changed={len(protected_changed_columns)}")
    print(f"pricing_decision_columns_changed={len(pricing_decision_changed_columns)}")
    print(f"scratch_columns_changed={len(scratch_changed_columns)}")
    print()
    print("INTEGRITY")
    print(f"score_range_errors={score_range_errors}")
    print(f"strict_prior_leakage={strict_prior_leakage}")
    print(f"invalid_live_rows={invalid_live_rows}")
    print(f"duplicate_profile_live_rows={duplicate_profile_live_rows}")
    print()
    print(f"FINAL STATUS: READY_FOR_INTELLIGENCE_UI={'YES' if ready else 'NO'}")


if __name__ == "__main__":
    main()
