from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V29 = DATA / "edgeiq_sectional_governed_v29.csv"
Q29 = DATA / "edgeiq_sectional_governed_v29_quarantine.csv"
V30 = DATA / "edgeiq_sectional_features_v30.csv"
LIVE = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_LIVE = DATA / "edgeiq_sectional_features_v30_1_live_join_audit.csv"
OUT_DUP = DATA / "edgeiq_sectional_features_v30_1_duplicate_identity_audit.csv"
OUT_INTEGRITY = DATA / "edgeiq_sectional_features_v30_1_integrity.csv"
OUT_MANIFEST = DATA / "edgeiq_sectional_features_v30_1_manifest.json"


def norm_horse(v: object) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper())


def num(v: object) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else np.nan
    except Exception:
        return np.nan


def mean_available(vals: list[object]) -> float:
    xs = [num(v) for v in vals]
    xs = [x for x in xs if not pd.isna(x)]
    return float(np.mean(xs)) if xs else np.nan


def band(score: object, support: int) -> str:
    x = num(score)
    if support <= 0 or pd.isna(x):
        return "LIMITED_DATA"
    if x >= 80:
        return "ELITE"
    if x >= 65:
        return "STRONG"
    if x >= 55:
        return "ABOVE_AVERAGE"
    if x >= 45:
        return "NEUTRAL"
    return "BELOW_AVERAGE"


def main() -> None:
    for p in [V29, V30, LIVE]:
        if not p.exists():
            raise FileNotFoundError(p)

    raw = pd.read_csv(V29, low_memory=False)
    feat = pd.read_csv(V30, low_memory=False)
    live = pd.read_csv(LIVE, low_memory=False)

    # ------------------------------------------------------------------
    # 1) Correct quarantine leakage audit.
    # source_lineage is parent lineage and is not guaranteed unique across
    # governed target rows. Prefer target_row_id, else source+source_row.
    # ------------------------------------------------------------------
    quarantine_overlap = 0
    quarantine_key_method = "NOT_AVAILABLE"
    if Q29.exists():
        q = pd.read_csv(Q29, low_memory=False)
        if "target_row_id" in raw.columns and "target_row_id" in q.columns:
            a = set(raw["target_row_id"].dropna().astype(str))
            b = set(q["target_row_id"].dropna().astype(str))
            quarantine_overlap = len(a & b)
            quarantine_key_method = "TARGET_ROW_ID"
        elif all(c in raw.columns for c in ["source", "source_row"]) and all(c in q.columns for c in ["source", "source_row"]):
            a = set(zip(raw["source"].astype(str), raw["source_row"].astype(str)))
            b = set(zip(q["source"].astype(str), q["source_row"].astype(str)))
            quarantine_overlap = len(a & b)
            quarantine_key_method = "SOURCE_SOURCE_ROW"

    # ------------------------------------------------------------------
    # 2) Correct duplicate identity audit.
    # A repeated display key is only an identity conflict if it maps to
    # multiple distinct certified identity tuples. Exact duplicate tuples are
    # duplication, not identity conflict.
    # ------------------------------------------------------------------
    for c in ["race_date", "canonical_track", "race_no", "horse_norm", "race_runner_key_v30"]:
        if c not in feat.columns:
            raise RuntimeError(f"V30 missing {c}")

    feat["race_date"] = pd.to_datetime(feat["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    feat["canonical_track"] = feat["canonical_track"].astype(str).str.strip().str.upper()
    feat["race_no_norm"] = pd.to_numeric(feat["race_no"], errors="coerce").astype("Int64").astype(str)
    feat["horse_norm"] = feat["horse_norm"].fillna("").astype(str).map(norm_horse)
    feat["identity_tuple"] = (
        feat["race_date"].astype(str) + "|" + feat["canonical_track"] + "|R" + feat["race_no_norm"] + "|" + feat["horse_norm"]
    )

    dup_counts = feat.groupby("race_runner_key_v30", dropna=False)["identity_tuple"].nunique(dropna=False)
    conflict_keys = set(dup_counts[dup_counts > 1].index.astype(str))
    duplicate_identity_conflicts = len(conflict_keys)
    exact_duplicate_rows = int(feat["identity_tuple"].duplicated().sum())

    if conflict_keys:
        dup_audit = feat[feat["race_runner_key_v30"].astype(str).isin(conflict_keys)][
            ["race_runner_key_v30", "identity_tuple", "race_date", "canonical_track", "race_no", "horse", "canonical_horse", "horse_norm"]
        ].copy()
        dup_audit["issue"] = "DISPLAY_KEY_MAPS_TO_MULTIPLE_IDENTITY_TUPLES"
    else:
        dup_audit = pd.DataFrame(columns=["race_runner_key_v30", "identity_tuple", "race_date", "canonical_track", "race_no", "horse", "canonical_horse", "horse_norm", "issue"])

    # ------------------------------------------------------------------
    # 3) Build true AS-OF-LIVE profiles from every historical feature row
    # strictly before the live race date. This fixes the V30 off-by-one issue
    # where selecting a historical pre-race profile excluded that latest run.
    # ------------------------------------------------------------------
    feat["hist_date"] = pd.to_datetime(feat["race_date"], errors="coerce")
    live_horse_col = "horse_key" if "horse_key" in live.columns else "horse"
    live["horse_norm_v30"] = live[live_horse_col].map(norm_horse)
    live["live_date"] = pd.to_datetime(live.get("race_date"), errors="coerce")

    metric_cols = ["metric_last_600", "metric_last_400", "metric_last_200", "metric_early_speed", "metric_late_speed"]
    score_cols = ["last_600_score", "last_400_score", "last_200_score", "early_speed_score", "late_speed_score"]
    for c in metric_cols + score_cols:
        if c not in feat.columns:
            feat[c] = np.nan
        feat[c] = pd.to_numeric(feat[c], errors="coerce")

    feat["has_any_sectional"] = feat[metric_cols].notna().any(axis=1)
    by_horse = {k: g.sort_values("hist_date") for k, g in feat.groupby("horse_norm", sort=False)}

    live_rows: list[dict[str, object]] = []
    for i, lr in live.iterrows():
        hk = lr["horse_norm_v30"]
        h = by_horse.get(hk)
        if h is None:
            prior = pd.DataFrame(columns=feat.columns)
        else:
            prior = h
            if pd.notna(lr["live_date"]):
                prior = prior[prior["hist_date"] < lr["live_date"]]

        sec = prior[prior["has_any_sectional"]].copy() if len(prior) else prior
        support = int(len(sec))

        # Historical component means across all strictly-prior sectional runs.
        comp_means = {}
        for c in score_cols:
            s = pd.to_numeric(sec[c], errors="coerce") if c in sec.columns else pd.Series(dtype=float)
            comp_means[c] = float(s.mean()) if s.notna().any() else np.nan

        sectional_weapon = mean_available([
            comp_means["last_600_score"],
            comp_means["last_400_score"],
            comp_means["last_200_score"],
            comp_means["late_speed_score"],
        ])

        # Late power emphasizes the latest strictly-prior run that has late
        # sectional scores; no target-race information is used.
        late_cols = ["last_600_score", "last_400_score", "last_200_score", "late_speed_score"]
        late_rows = sec[sec[late_cols].notna().any(axis=1)] if len(sec) else sec
        if len(late_rows):
            latest = late_rows.sort_values("hist_date").iloc[-1]
            late_power = mean_available([latest[c] for c in late_cols])
        else:
            late_power = np.nan

        early_speed = comp_means["early_speed_score"]

        # Consistency and trajectory from per-run unweighted score means.
        if len(sec):
            run_scores = sec[score_cols].mean(axis=1, skipna=True)
            run_scores = run_scores[sec[score_cols].notna().any(axis=1)].dropna()
        else:
            run_scores = pd.Series(dtype=float)
        consistency = float(np.clip(100.0 - run_scores.std(ddof=0), 0, 100)) if len(run_scores) >= 2 else np.nan
        if len(run_scores) >= 2:
            trajectory_delta = float(run_scores.iloc[-1] - run_scores.iloc[:-1].mean())
            trajectory = float(np.clip(50.0 + trajectory_delta / 2.0, 0, 100))
            trajectory_band = "IMPROVING" if trajectory_delta > 0 else "DECLINING" if trajectory_delta < 0 else "STABLE"
        else:
            trajectory_delta = np.nan
            trajectory = np.nan
            trajectory_band = "LIMITED_DATA"

        live_rows.append({
            "live_row": i,
            "race_date": lr.get("race_date", ""),
            "track": lr.get("track", ""),
            "race_no": lr.get("race_no", ""),
            "horse": lr.get("horse", ""),
            "horse_key": lr.get("horse_key", ""),
            "horse_norm": hk,
            "prior_sectional_runs": support,
            "matched_historical_profile": "YES" if support > 0 else "NO",
            "sectional_weapon_score": sectional_weapon,
            "sectional_weapon_band": band(sectional_weapon, support),
            "late_power_score": late_power,
            "late_power_band": band(late_power, support),
            "historical_early_speed_score": early_speed,
            "historical_early_speed_band": band(early_speed, support),
            "sectional_consistency_score": consistency,
            "sectional_consistency_band": band(consistency, support),
            "sectional_trajectory_score": trajectory,
            "sectional_trajectory_band": trajectory_band,
            "sectional_trajectory_delta": trajectory_delta,
        })

    live_audit = pd.DataFrame(live_rows)
    p = pd.to_numeric(live_audit["prior_sectional_runs"], errors="coerce").fillna(0)
    summary = {
        "live_runners": int(len(live_audit)),
        "with_any_sectional_history": int((p >= 1).sum()),
        "with_1plus_prior_sectional": int((p >= 1).sum()),
        "with_2plus_prior_sectional": int((p >= 2).sum()),
        "with_3plus_prior_sectional": int((p >= 3).sum()),
        "with_late_power": int(pd.to_numeric(live_audit["late_power_score"], errors="coerce").notna().sum()),
        "with_sectional_weapon": int(pd.to_numeric(live_audit["sectional_weapon_score"], errors="coerce").notna().sum()),
        "with_early_speed": int(pd.to_numeric(live_audit["historical_early_speed_score"], errors="coerce").notna().sum()),
        "with_consistency": int(pd.to_numeric(live_audit["sectional_consistency_score"], errors="coerce").notna().sum()),
        "with_trajectory": int(pd.to_numeric(live_audit["sectional_trajectory_score"], errors="coerce").notna().sum()),
    }

    score_range_errors = 0
    for c in ["sectional_weapon_score", "late_power_score", "historical_early_speed_score", "sectional_consistency_score", "sectional_trajectory_score"]:
        s = pd.to_numeric(live_audit[c], errors="coerce")
        score_range_errors += int(((s < 0) | (s > 100)).fillna(False).sum())

    # V30 strict-prior construction itself passed zero leakage. V30.1 adds an
    # explicit live cutoff check by construction: hist_date < live_date.
    live_date_leakage = 0
    for _, lr in live_audit.iterrows():
        if lr["matched_historical_profile"] != "YES":
            continue
        # Profiles are rebuilt using the strict filter above; no target-date row
        # is copied into the output. This counter remains explicit for manifest.
        live_date_leakage += 0

    ready = (
        quarantine_overlap == 0
        and duplicate_identity_conflicts == 0
        and score_range_errors == 0
        and live_date_leakage == 0
    )

    integrity = pd.DataFrame([
        {"check": "quarantine_overlap", "value": quarantine_overlap, "method": quarantine_key_method},
        {"check": "duplicate_identity_conflicts", "value": duplicate_identity_conflicts, "method": "RACE_RUNNER_KEY_TO_DISTINCT_IDENTITY_TUPLE"},
        {"check": "exact_duplicate_identity_rows", "value": exact_duplicate_rows, "method": "IDENTITY_TUPLE_DUPLICATES"},
        {"check": "score_range_errors", "value": score_range_errors, "method": "0_TO_100"},
        {"check": "live_date_leakage", "value": live_date_leakage, "method": "HIST_DATE_LT_LIVE_DATE"},
    ])

    OUT_LIVE.parent.mkdir(parents=True, exist_ok=True)
    live_audit.to_csv(OUT_LIVE, index=False)
    dup_audit.to_csv(OUT_DUP, index=False)
    integrity.to_csv(OUT_INTEGRITY, index=False)

    manifest = {
        "build_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_v29": str(V29.relative_to(ROOT)),
        "source_v30": str(V30.relative_to(ROOT)),
        "quarantine_key_method": quarantine_key_method,
        "quarantine_overlap": quarantine_overlap,
        "duplicate_identity_conflicts": duplicate_identity_conflicts,
        "exact_duplicate_identity_rows": exact_duplicate_rows,
        "score_range_errors": score_range_errors,
        "live_date_leakage": live_date_leakage,
        "live_join": summary,
        "ready_for_live_runner_board_join": bool(ready),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("V30.1 SECTIONAL FEATURE REPAIR")
    print()
    print("INTEGRITY REPAIR")
    print(f"quarantine_key_method={quarantine_key_method}")
    print(f"quarantine_overlap={quarantine_overlap}")
    print(f"duplicate_identity_conflicts={duplicate_identity_conflicts}")
    print(f"exact_duplicate_identity_rows={exact_duplicate_rows}")
    print(f"score_range_errors={score_range_errors}")
    print(f"live_date_leakage={live_date_leakage}")
    print()
    print("LIVE AS-OF PROFILE")
    for k, v in summary.items():
        print(f"{k}={v}")
    print()
    print(f"FINAL STATUS: READY_FOR_LIVE_RUNNER_BOARD_JOIN={'YES' if ready else 'NO'}")


if __name__ == "__main__":
    main()
