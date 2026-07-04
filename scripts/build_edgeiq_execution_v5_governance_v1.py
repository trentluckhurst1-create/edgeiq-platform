from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_FILE = os.path.join(DATA, "edgeiq_environment_score_replay_v1.csv")

OUT = os.path.join(DATA, "edgeiq_execution_v5_governance_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_execution_v5_governance_v1_summary.csv")
OUT_BY_YEAR = os.path.join(DATA, "edgeiq_execution_v5_governance_v1_by_year.csv")
OUT_BY_TRUST = os.path.join(DATA, "edgeiq_execution_v5_governance_v1_by_trust.csv")
OUT_BY_FIELD = os.path.join(DATA, "edgeiq_execution_v5_governance_v1_by_field_size.csv")
OUT_AUDIT = os.path.join(DATA, "edgeiq_execution_v5_governance_v1_audit.csv")


def num(x):
    return pd.to_numeric(x, errors="coerce")


def pct(x):
    if pd.isna(x):
        return None
    return round(float(x) * 100.0, 2)


def governance(score):
    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 5:
        return "V5_ENVIRONMENT_STRONG"
    if s >= 3:
        return "V5_ENVIRONMENT_APPROVED"
    return "V5_ENVIRONMENT_REJECT"


def action(score):
    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 5:
        return "EXECUTE_STRONG_ENVIRONMENT"
    if s >= 3:
        return "EXECUTE_ENVIRONMENT_APPROVED"
    return "NO_LIVE_LOW_ENVIRONMENT"


def reason(row):
    score = row.get("environment_score_v1", "")
    band = row.get("environment_band_v1", "")
    env_reason = row.get("environment_reason_v1", "")

    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 5:
        return f"Strong V5 environment: score {score}, band {band}. {env_reason}"
    if s >= 3:
        return f"Approved V5 environment: score {score}, band {band}. {env_reason}"
    return f"Rejected by V5 environment governance: score {score}, band {band}. {env_reason}"


def summarise(df, segment):
    if len(df) == 0:
        return {
            "segment": segment,
            "signals": 0,
            "races": 0,
            "wins": 0,
            "places": 0,
            "win_rate_pct": None,
            "place_rate_pct": None,
            "avg_environment_score": None,
            "avg_score_share": None,
            "avg_dominance": None,
            "avg_edge_proxy_pct": None,
        }

    return {
        "segment": segment,
        "signals": int(len(df)),
        "races": int(df["race_join_key_fixed"].nunique()) if "race_join_key_fixed" in df.columns else int(len(df)),
        "wins": int(df["won_final"].sum()),
        "places": int(df["placed_final"].sum()),
        "win_rate_pct": pct(df["won_final"].mean()),
        "place_rate_pct": pct(df["placed_final"].mean()),
        "avg_environment_score": round(float(df["environment_score_num"].mean()), 3),
        "avg_score_share": round(float(df["score_share_num"].mean()), 6) if df["score_share_num"].notna().any() else None,
        "avg_dominance": round(float(df["dominance_num"].mean()), 3) if df["dominance_num"].notna().any() else None,
        "avg_edge_proxy_pct": round(float(df["edge_proxy_num"].mean()), 3) if df["edge_proxy_num"].notna().any() else None,
    }


def group_report(df, cols, prefix):
    rows = []

    for keys, g in df.groupby(cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        row = summarise(g, prefix + "__" + "__".join([str(k) for k in keys]))

        for c, k in zip(cols, keys):
            row[c] = k

        rows.append(row)

    return pd.DataFrame(rows)


def main():
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(IN_FILE)

    df = pd.read_csv(IN_FILE, low_memory=False)

    if "won_num" in df.columns:
        df["won_final"] = num(df["won_num"]).fillna(0).astype(int)
        win_source = "won_num"
    elif "won" in df.columns:
        df["won_final"] = num(df["won"]).fillna(0).astype(int)
        win_source = "won"
    elif "finish_position" in df.columns:
        df["won_final"] = (num(df["finish_position"]) == 1).astype(int)
        win_source = "finish_position"
    else:
        raise ValueError("No win column found")

    if "placed_num" in df.columns:
        df["placed_final"] = num(df["placed_num"]).fillna(0).astype(int)
        place_source = "placed_num"
    elif "placed" in df.columns:
        df["placed_final"] = num(df["placed"]).fillna(0).astype(int)
        place_source = "placed"
    elif "finish_position" in df.columns:
        fp = num(df["finish_position"])
        df["placed_final"] = ((fp >= 1) & (fp <= 3)).astype(int)
        place_source = "finish_position"
    else:
        df["placed_final"] = 0
        place_source = "none"

    df["environment_score_num"] = num(df["environment_score_v1"]).fillna(0)
    df["score_share_num"] = num(df.get("score_share_of_race"))
    df["dominance_num"] = num(df.get("dominance_score_v1"))
    df["edge_proxy_num"] = num(df.get("edge_proxy_pct"))

    if "meeting_date" in df.columns:
        df["year"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    elif "race_date" in df.columns:
        df["year"] = pd.to_datetime(df["race_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    else:
        df["year"] = "UNKNOWN"

    df["v5_environment_governance_v1"] = df["environment_score_num"].map(governance)
    df["v5_environment_execution_action_v1"] = df["environment_score_num"].map(action)
    df["v5_environment_governance_reason_v1"] = df.apply(reason, axis=1)

    base = summarise(df, "BASE_V4")
    reject = summarise(df[df["v5_environment_governance_v1"] == "V5_ENVIRONMENT_REJECT"], "V5_REJECT_LOW_ENVIRONMENT")
    approved = summarise(df[df["v5_environment_governance_v1"] == "V5_ENVIRONMENT_APPROVED"], "V5_APPROVED_ENVIRONMENT")
    strong = summarise(df[df["v5_environment_governance_v1"] == "V5_ENVIRONMENT_STRONG"], "V5_STRONG_ENVIRONMENT")
    approved_plus = summarise(df[df["v5_environment_governance_v1"].isin(["V5_ENVIRONMENT_APPROVED", "V5_ENVIRONMENT_STRONG"])], "V5_APPROVED_PLUS_STRONG")

    summary = pd.DataFrame([base, reject, approved, strong, approved_plus])

    base_wr = float(base["win_rate_pct"])

    summary["lift_vs_base_points"] = summary["win_rate_pct"].apply(
        lambda x: round(float(x) - base_wr, 3) if pd.notna(x) else None
    )

    by_year = group_report(df, ["year", "v5_environment_governance_v1"], "YEAR_GOVERNANCE")
    by_trust = group_report(df, ["trust_profile_v1", "v5_environment_governance_v1"], "TRUST_GOVERNANCE")
    by_field = group_report(df, ["field_size_bucket_v1", "v5_environment_governance_v1"], "FIELD_GOVERNANCE")

    for frame in [by_year, by_trust, by_field]:
        if len(frame):
            frame["lift_vs_base_points"] = frame["win_rate_pct"].apply(
                lambda x: round(float(x) - base_wr, 3) if pd.notna(x) else None
            )

    approved_lift = float(approved_plus["win_rate_pct"]) - base_wr
    reject_lift = float(reject["win_rate_pct"]) - base_wr

    if approved_plus["signals"] >= 1000 and approved_lift >= 3 and reject_lift < 0:
        verdict = "V5_GOVERNANCE_READY"
    elif approved_lift > 0 and reject_lift < 0:
        verdict = "V5_GOVERNANCE_READY_WITH_CAUTION"
    else:
        verdict = "V5_GOVERNANCE_NOT_READY"

    audit = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "input_file", "value": IN_FILE},
        {"metric": "rows", "value": len(df)},
        {"metric": "win_source", "value": win_source},
        {"metric": "place_source", "value": place_source},
        {"metric": "base_win_rate_pct", "value": base["win_rate_pct"]},
        {"metric": "reject_signals", "value": reject["signals"]},
        {"metric": "reject_win_rate_pct", "value": reject["win_rate_pct"]},
        {"metric": "approved_signals", "value": approved["signals"]},
        {"metric": "approved_win_rate_pct", "value": approved["win_rate_pct"]},
        {"metric": "strong_signals", "value": strong["signals"]},
        {"metric": "strong_win_rate_pct", "value": strong["win_rate_pct"]},
        {"metric": "approved_plus_signals", "value": approved_plus["signals"]},
        {"metric": "approved_plus_win_rate_pct", "value": approved_plus["win_rate_pct"]},
        {"metric": "approved_plus_lift_points", "value": round(float(approved_lift), 3)},
        {"metric": "reject_lift_points", "value": round(float(reject_lift), 3)},
        {"metric": "verdict", "value": verdict},
    ])

    wanted = [
        "meeting_date",
        "race_date",
        "track",
        "race_no",
        "horse",
        "race_join_key_fixed",
        "runner_join_key_fixed",
        "runner_rank",
        "runner_score",
        "score_share_of_race",
        "score_share_band_v1",
        "dominance_score_v1",
        "dominance_band_v1",
        "trust_profile_v1",
        "trust_band_v1",
        "field_size",
        "field_size_bucket_v1",
        "edge_proxy_pct",
        "won_final",
        "placed_final",
        "finish_position",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "pace_advantage_band_v1",
        "pace_advantage_score_v1",
        "pace_role_v1",
        "race_shape_density_v1",
        "lone_leader_bool",
        "race_strength_band",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "v5_environment_governance_v1",
        "v5_environment_execution_action_v1",
        "v5_environment_governance_reason_v1",
    ]

    wanted = [c for c in wanted if c in df.columns]

    df[wanted].to_csv(OUT, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    by_year.to_csv(OUT_BY_YEAR, index=False)
    by_trust.to_csv(OUT_BY_TRUST, index=False)
    by_field.to_csv(OUT_BY_FIELD, index=False)
    audit.to_csv(OUT_AUDIT, index=False)

    print("[EXECUTION_V5_GOVERNANCE_V1] COMPLETE")
    print(f"win_source={win_source}")
    print(f"place_source={place_source}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_YEAR}")
    print(f"wrote={OUT_BY_TRUST}")
    print(f"wrote={OUT_BY_FIELD}")
    print(f"wrote={OUT_AUDIT}")


if __name__ == "__main__":
    main()
