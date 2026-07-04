from __future__ import annotations

import pandas as pd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ENV_SRC = DATA / "edgeiq_environment_score_replay_v1.csv"
SP_SRC = DATA / "edgeiq_rank1_sp_history_v1.csv"

OUT = DATA / "edgeiq_environment_market_audit_v2.csv"
SUMMARY = DATA / "edgeiq_environment_market_audit_v2_summary.csv"
VERDICT = DATA / "edgeiq_environment_market_audit_v2_verdict.csv"

ENV_BANDS = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]


def as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def summarise_segment(label: str, df: pd.DataFrame) -> dict[str, object]:
    runners = len(df)
    wins = int(as_numeric(df["environment_win_v1"]).fillna(0).sum()) if runners else 0
    win_pct = wins / runners * 100 if runners else 0.0

    sp_num = as_numeric(df["sp_num_v1"])
    valid_mask = sp_num.notna() & (sp_num > 1)
    valid = df[valid_mask].copy()
    valid_sp = as_numeric(valid["sp_num_v1"])

    valid_runners = len(valid)
    valid_wins = int(as_numeric(valid["environment_win_v1"]).fillna(0).sum()) if valid_runners else 0
    valid_win_pct = valid_wins / valid_runners * 100 if valid_runners else 0.0

    expected_wins = float((1 / valid_sp).sum()) if valid_runners else 0.0
    ae = (valid_wins / expected_wins) if expected_wins > 0 else None

    profit = 0.0
    if valid_runners:
        profit = float(((valid_sp - 1.0) * as_numeric(valid["environment_win_v1"]).fillna(0) - (1 - as_numeric(valid["environment_win_v1"]).fillna(0))).sum())

    roi_pct = (profit / valid_runners * 100) if valid_runners else None
    avg_sp = float(valid_sp.mean()) if valid_runners else None
    coverage_pct = (valid_runners / runners * 100) if runners else 0.0

    return {
        "segment": label,
        "runners": int(runners),
        "wins": wins,
        "win_pct": round(win_pct, 2),
        "valid_sp_runners": int(valid_runners),
        "valid_sp_wins": valid_wins,
        "valid_sp_win_pct": round(valid_win_pct, 2),
        "avg_sp": round(avg_sp, 3) if avg_sp is not None else "",
        "expected_wins": round(expected_wins, 3) if valid_runners else "",
        "ae": round(ae, 3) if ae is not None else "",
        "profit_1u": round(profit, 3) if valid_runners else "",
        "roi_pct": round(roi_pct, 2) if roi_pct is not None else "",
        "sp_coverage_pct": round(coverage_pct, 2),
    }


def metric_value(frame: pd.DataFrame, segment: str, column: str) -> float | None:
    row = frame[frame["segment"] == segment]
    if row.empty:
        return None
    value = row.iloc[0][column]
    if value == "" or pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def main() -> None:
    if not ENV_SRC.exists():
        raise SystemExit("Missing edgeiq_environment_score_replay_v1.csv")
    if not SP_SRC.exists():
        raise SystemExit("Missing edgeiq_rank1_sp_history_v1.csv. Run build_edgeiq_rank1_sp_history_v1.py first.")

    env = pd.read_csv(ENV_SRC, low_memory=False)
    sp = pd.read_csv(SP_SRC, low_memory=False)

    required_env = ["join_key_v1", "environment_band_v1", "environment_win_v1"]
    required_sp = ["join_key_v1", "sp", "sp_num_v1", "sp_valid_v1", "sp_join_status_v1"]

    missing_env = [col for col in required_env if col not in env.columns]
    missing_sp = [col for col in required_sp if col not in sp.columns]
    if missing_env:
        raise SystemExit("Environment replay missing columns: " + ", ".join(missing_env))
    if missing_sp:
        raise SystemExit("SP history missing columns: " + ", ".join(missing_sp))

    sp_small = sp[["join_key_v1", "sp", "sp_num_v1", "sp_valid_v1", "sp_join_status_v1"]].copy()
    sp_small = sp_small.drop_duplicates("join_key_v1")

    df = env.merge(sp_small, on="join_key_v1", how="left")
    df["environment_band_v1"] = df["environment_band_v1"].fillna("").astype(str).str.upper()

    rows: list[dict[str, object]] = []
    rows.append(summarise_segment("ALL", df))

    for band in ENV_BANDS:
        rows.append(summarise_segment(band, df[df["environment_band_v1"] == band]))

    rows.append(summarise_segment("WEAK_POOR_NEGATIVE", df[df["environment_band_v1"].isin(["POOR", "NEGATIVE"])]))
    rows.append(summarise_segment("NEUTRAL_ONLY", df[df["environment_band_v1"] == "NEUTRAL"]))
    rows.append(summarise_segment("STRONG_POSITIVE_ELITE", df[df["environment_band_v1"].isin(["POSITIVE", "ELITE"])]))

    audit_df = pd.DataFrame(rows)
    audit_df.to_csv(OUT, index=False)

    coverage = metric_value(audit_df, "ALL", "sp_coverage_pct") or 0.0
    elite_ae = metric_value(audit_df, "ELITE", "ae")
    weak_ae = metric_value(audit_df, "WEAK_POOR_NEGATIVE", "ae")
    strong_ae = metric_value(audit_df, "STRONG_POSITIVE_ELITE", "ae")
    elite_roi = metric_value(audit_df, "ELITE", "roi_pct")
    weak_roi = metric_value(audit_df, "WEAK_POOR_NEGATIVE", "roi_pct")
    strong_roi = metric_value(audit_df, "STRONG_POSITIVE_ELITE", "roi_pct")

    verdict = "ENVIRONMENT_MARKET_EDGE_NOT_CONFIRMED"
    if coverage < 70.0:
        verdict = "SP_COVERAGE_INSUFFICIENT"
    elif elite_ae is not None and elite_ae > 1.0:
        verdict = "ENVIRONMENT_MARKET_EDGE_CONFIRMED"
    elif strong_ae is not None and weak_ae is not None and strong_ae > weak_ae:
        verdict = "ENVIRONMENT_MARKET_SHAPE_CONFIRMED"

    summary_df = pd.DataFrame(
        [
            {"metric": "rows", "value": int(len(df))},
            {"metric": "valid_sp_rows", "value": int((as_numeric(df["sp_num_v1"]).notna() & (as_numeric(df["sp_num_v1"]) > 1)).sum())},
            {"metric": "sp_coverage_pct", "value": round(coverage, 2)},
            {"metric": "elite_ae", "value": elite_ae if elite_ae is not None else ""},
            {"metric": "weak_ae", "value": weak_ae if weak_ae is not None else ""},
            {"metric": "strong_ae", "value": strong_ae if strong_ae is not None else ""},
            {"metric": "elite_roi_pct", "value": elite_roi if elite_roi is not None else ""},
            {"metric": "weak_roi_pct", "value": weak_roi if weak_roi is not None else ""},
            {"metric": "strong_roi_pct", "value": strong_roi if strong_roi is not None else ""},
            {"metric": "verdict", "value": verdict},
        ]
    )
    summary_df.to_csv(SUMMARY, index=False)

    verdict_df = pd.DataFrame(
        [
            {
                "verdict": verdict,
                "coverage_pct": round(coverage, 2),
                "elite_ae": elite_ae if elite_ae is not None else "",
                "strong_positive_elite_ae": strong_ae if strong_ae is not None else "",
                "weak_poor_negative_ae": weak_ae if weak_ae is not None else "",
                "important_note": "This audit uses full Racing.com warehouse SP joins for Rank1 history only; no Environment V1 rules were altered.",
            }
        ]
    )
    verdict_df.to_csv(VERDICT, index=False)

    print("[EDGEIQ_ENVIRONMENT_MARKET_AUDIT_V2] COMPLETE")
    print(f"rows={len(df)}")
    print(f"coverage={round(coverage, 2)}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={VERDICT}")


if __name__ == "__main__":
    main()
