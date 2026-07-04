from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import math
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_live_runner_board_v1.csv"
AUDIT = DATA / "edgeiq_no_projection_fallback_adjustment_v1.csv"
SUMMARY = DATA / "edgeiq_no_projection_fallback_adjustment_summary_v1.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

RATED_POOL = 0.85
FALLBACK_POOL = 0.15
MAX_FALLBACK_PER_RUNNER = 0.08
MIN_FALLBACK_PER_RUNNER = 0.005

def clean(x):
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return str(x).strip()

def num(x):
    try:
        s = clean(x)
        if s == "":
            return None
        v = float(s)
        if not math.isfinite(v):
            return None
        return v
    except Exception:
        return None

def fmt(x, places=2):
    if x is None:
        return ""
    try:
        v = float(x)
        if not math.isfinite(v):
            return ""
        return str(round(v, places))
    except Exception:
        return ""

def race_no_num(x):
    n = re.sub(r"[^0-9]", "", clean(x))
    return int(n) if n else 9999

def is_scratched(row):
    txt = " ".join([
        clean(row.get("display_decision")).upper(),
        clean(row.get("runner_status")).upper(),
        clean(row.get("tab_fixed_betting_status")).upper(),
        clean(row.get("scratch_status")).upper(),
        clean(row.get("is_scratched")).upper(),
    ])
    return "SCRATCH" in txt or "LATESCRATCHED" in txt

def implied_from_live(row):
    live = num(row.get("display_live_price")) or num(row.get("live_price")) or num(row.get("tab_fixed_win"))
    if live is None or live <= 1.01:
        return None
    return 1.0 / live

def decision(live, fair, edge, status):
    if status == "SCRATCHED":
        return "SCRATCHED"
    if live is None or live <= 0:
        return "NO MARKET"
    if fair is None or fair <= 0:
        return "NO MODEL"
    if edge is None:
        return "NO EDGE"
    if edge >= 18:
        return "WATCH"
    if edge >= 10:
        return "LEAN"
    if edge > 0:
        return "PASS"
    return "UNDERLAY"

def main():
    if not INP.exists():
        raise SystemExit(f"Missing {INP}")

    df = pd.read_csv(INP, dtype=str, keep_default_na=False, low_memory=False)
    if df.empty:
        raise SystemExit(f"Empty {INP}")

    required = [
        "race_date","track","race_no","horse","runner_status",
        "V6_1_RESEARCH_price_status","V6_1_RESEARCH_probability",
        "display_live_price","live_price","tab_fixed_win",
        "display_decision","display_fair_price","fair_price",
        "rated_price","ui_fair_price","display_edge_pct","edge_pct","ui_edge_pct",
        "win_pct","execution_action"
    ]
    for c in required:
        if c not in df.columns:
            df[c] = ""

    df["scratch_bool_tmp"] = df.apply(is_scratched, axis=1)
    df["active_bool_tmp"] = ~df["scratch_bool_tmp"]

    audit_rows = []

    for race_no, idx in df.groupby("race_no", dropna=False).groups.items():
        race_idx = list(idx)
        race = df.loc[race_idx].copy()

        active = race[~race["scratch_bool_tmp"]].copy()
        if active.empty:
            continue

        rated_mask = (
            active["V6_1_RESEARCH_price_status"].eq("RESEARCH_RATED") &
            active["V6_1_RESEARCH_probability"].map(clean).ne("")
        )
        fallback_mask = (
            active["V6_1_RESEARCH_price_status"].isin(["NO_PRICE", "NO_PROJECTION_FALLBACK"]) |
            active["V6_1_RESEARCH_price_status"].map(clean).eq("")
        )

        rated_idx = active[rated_mask].index.tolist()
        fallback_idx = active[fallback_mask].index.tolist()

        rated_probs_raw = []
        for ridx in rated_idx:
            p = num(df.at[ridx, "V6_1_RESEARCH_probability"])
            rated_probs_raw.append(0.0 if p is None else p)
        rated_raw_sum = sum(rated_probs_raw)

        fallback_weights = []
        for fidx in fallback_idx:
            imp = implied_from_live(df.loc[fidx])
            fallback_weights.append(0.0 if imp is None else imp)
        fallback_weight_sum = sum(fallback_weights)

        if rated_idx and fallback_idx:
            # rated runners share 85%; no-projection runners share 15%, market-weighted.
            for ridx, raw_p in zip(rated_idx, rated_probs_raw):
                adj_p = (raw_p / rated_raw_sum) * RATED_POOL if rated_raw_sum > 0 else RATED_POOL / len(rated_idx)
                live = num(df.at[ridx, "display_live_price"]) or num(df.at[ridx, "live_price"])
                fair = 1.0 / adj_p if adj_p > 0 else None
                edge = ((live / fair) - 1.0) * 100.0 if live and fair else None

                df.at[ridx, "V6_1_RESEARCH_probability"] = fmt(adj_p, 6)
                df.at[ridx, "win_pct"] = fmt(adj_p * 100.0, 2)
                df.at[ridx, "fair_price"] = fmt(fair, 2)
                df.at[ridx, "rated_price"] = fmt(fair, 2)
                df.at[ridx, "ui_fair_price"] = fmt(fair, 2)
                df.at[ridx, "display_fair_price"] = fmt(fair, 2)
                df.at[ridx, "edge_pct"] = fmt(edge, 1)
                df.at[ridx, "ui_edge_pct"] = fmt(edge, 1)
                df.at[ridx, "display_edge_pct"] = fmt(edge, 1)
                df.at[ridx, "display_decision"] = decision(live, fair, edge, "ACTIVE")
                df.at[ridx, "execution_action"] = df.at[ridx, "display_decision"]

            for fidx, weight in zip(fallback_idx, fallback_weights):
                if fallback_weight_sum > 0:
                    adj_p = (weight / fallback_weight_sum) * FALLBACK_POOL
                else:
                    adj_p = FALLBACK_POOL / len(fallback_idx)

                adj_p = max(MIN_FALLBACK_PER_RUNNER, min(MAX_FALLBACK_PER_RUNNER, adj_p))

                live = num(df.at[fidx, "display_live_price"]) or num(df.at[fidx, "live_price"])
                fair = 1.0 / adj_p if adj_p > 0 else None
                edge = ((live / fair) - 1.0) * 100.0 if live and fair else None

                df.at[fidx, "V6_1_RESEARCH_probability"] = fmt(adj_p, 6)
                df.at[fidx, "win_pct"] = fmt(adj_p * 100.0, 2)
                df.at[fidx, "fair_price"] = fmt(fair, 2)
                df.at[fidx, "rated_price"] = fmt(fair, 2)
                df.at[fidx, "ui_fair_price"] = fmt(fair, 2)
                df.at[fidx, "display_fair_price"] = fmt(fair, 2)
                df.at[fidx, "edge_pct"] = fmt(edge, 1)
                df.at[fidx, "ui_edge_pct"] = fmt(edge, 1)
                df.at[fidx, "display_edge_pct"] = fmt(edge, 1)
                df.at[fidx, "display_decision"] = decision(live, fair, edge, "ACTIVE")
                df.at[fidx, "execution_action"] = df.at[fidx, "display_decision"]
                df.at[fidx, "V6_1_RESEARCH_price_status"] = "NO_PROJECTION_FALLBACK"
                if "V6_1_RESEARCH_price_bucket" in df.columns:
                    df.at[fidx, "V6_1_RESEARCH_price_bucket"] = "FALLBACK"

            # Re-normalize after fallback caps/floors.
            active_indices = rated_idx + fallback_idx
            total = 0.0
            for aidx in active_indices:
                p = num(df.at[aidx, "V6_1_RESEARCH_probability"])
                total += 0.0 if p is None else p

            if total > 0:
                for aidx in active_indices:
                    p = num(df.at[aidx, "V6_1_RESEARCH_probability"]) or 0.0
                    adj_p = p / total
                    live = num(df.at[aidx, "display_live_price"]) or num(df.at[aidx, "live_price"])
                    fair = 1.0 / adj_p if adj_p > 0 else None
                    edge = ((live / fair) - 1.0) * 100.0 if live and fair else None

                    df.at[aidx, "V6_1_RESEARCH_probability"] = fmt(adj_p, 6)
                    df.at[aidx, "win_pct"] = fmt(adj_p * 100.0, 2)
                    df.at[aidx, "fair_price"] = fmt(fair, 2)
                    df.at[aidx, "rated_price"] = fmt(fair, 2)
                    df.at[aidx, "ui_fair_price"] = fmt(fair, 2)
                    df.at[aidx, "display_fair_price"] = fmt(fair, 2)
                    df.at[aidx, "edge_pct"] = fmt(edge, 1)
                    df.at[aidx, "ui_edge_pct"] = fmt(edge, 1)
                    df.at[aidx, "display_edge_pct"] = fmt(edge, 1)
                    df.at[aidx, "display_decision"] = decision(live, fair, edge, "ACTIVE")
                    df.at[aidx, "execution_action"] = df.at[aidx, "display_decision"]

        # Scratched remain blank model-side.
        scratched_idx = race[race["scratch_bool_tmp"]].index.tolist()
        for sidx in scratched_idx:
            for col in [
                "V6_1_RESEARCH_probability","win_pct","fair_price","rated_price",
                "ui_fair_price","display_fair_price","edge_pct","ui_edge_pct","display_edge_pct"
            ]:
                df.at[sidx, col] = ""
            df.at[sidx, "display_decision"] = "SCRATCHED"
            df.at[sidx, "execution_action"] = "SCRATCHED"

        active_after = df.loc[active.index]
        prob_sum = sum((num(v) or 0.0) for v in active_after["V6_1_RESEARCH_probability"])

        audit_rows.append({
            "race_no": race_no,
            "active_runners": len(active),
            "rated_runners": len(rated_idx),
            "fallback_runners": len(fallback_idx),
            "scratched_runners": len(scratched_idx),
            "probability_sum_after": round(prob_sum, 6),
            "rated_pool_target": RATED_POOL if rated_idx and fallback_idx else "",
            "fallback_pool_target": FALLBACK_POOL if rated_idx and fallback_idx else "",
        })

    df = df.drop(columns=["scratch_bool_tmp","active_bool_tmp"], errors="ignore")

    df["race_no_sort_tmp"] = df["race_no"].map(race_no_num)
    if "horse_no" in df.columns:
        df["horse_no_sort_tmp"] = pd.to_numeric(df["horse_no"], errors="coerce").fillna(9999)
    else:
        df["horse_no_sort_tmp"] = 9999
    df = df.sort_values(["race_no_sort_tmp","horse_no_sort_tmp","horse"]).drop(columns=["race_no_sort_tmp","horse_no_sort_tmp"])

    df.to_csv(OUT, index=False)

    audit = pd.DataFrame(audit_rows).sort_values("race_no")
    audit.to_csv(AUDIT, index=False)

    summary = pd.DataFrame([
        ["status", "COMPLETE"],
        ["today", TODAY],
        ["rows", len(df)],
        ["active_rows", int((df["display_decision"] != "SCRATCHED").sum())],
        ["fallback_rows", int((df["V6_1_RESEARCH_price_status"] == "NO_PROJECTION_FALLBACK").sum())],
        ["research_rated_rows", int((df["V6_1_RESEARCH_price_status"] == "RESEARCH_RATED").sum())],
        ["scratched_rows", int((df["display_decision"] == "SCRATCHED").sum())],
        ["watch_rows", int((df["display_decision"] == "WATCH").sum())],
        ["lean_rows", int((df["display_decision"] == "LEAN").sum())],
        ["pass_rows", int((df["display_decision"] == "PASS").sum())],
        ["underlay_rows", int((df["display_decision"] == "UNDERLAY").sum())],
        ["no_model_rows", int((df["display_decision"] == "NO MODEL").sum())],
    ], columns=["metric","value"])
    summary.to_csv(SUMMARY, index=False)

    print("[NO_PROJECTION_FALLBACK_ADJUSTMENT_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"out={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
