from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CARD = DATA / "race_card_report.csv"
TAB = DATA / "edgeiq_tab_live_prices_direct_v1.csv"
REPLAY = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"

OUT = DATA / "edgeiq_probability_scratch_audit_v1.csv"
SUMMARY = DATA / "edgeiq_probability_scratch_audit_summary_v1.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
DISPLAY_TRACK = "PAKENHAM SYNTHETIC"
SOURCE_TRACKS = {
    "PAKENHAM",
    "PAKENHAM SYNTHETIC",
    "SOUTHSIDE PAKENHAM SYNTHETIC",
}


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def num(value: object) -> float | None:
    text = clean(value).replace("$", "").replace(",", "").replace("%", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|GB|IRE|USA|FR|JPN|SAF|GER|CAN)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def norm_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def canonical_track(value: object) -> str:
    track = norm_track(value)
    return DISPLAY_TRACK if track in SOURCE_TRACKS else track


def race_no_int(value: object) -> int:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return int(digits) if digits else 0


def implied_probability(fair_price: float | None) -> float:
    if fair_price is None or fair_price <= 0:
        return 0.0
    return 1.0 / fair_price


def edge_pct(live_price: float | None, fair_price: float | None) -> float | None:
    if live_price is None or live_price <= 0 or fair_price is None or fair_price <= 0:
        return None
    return ((live_price / fair_price) - 1.0) * 100.0


def decision_from_edge(live_price: float | None, edge_value: float | None, scratched: bool) -> str:
    if scratched:
        return "SCRATCHED"
    if live_price is None or live_price <= 0:
        return "NO MARKET"
    if edge_value is None:
        return "PASS"
    if edge_value >= 18.0:
        return "WATCH"
    if edge_value >= 10.0:
        return "LEAN"
    if edge_value > 0.0:
        return "PASS"
    return "UNDERLAY"


def main() -> None:
    if not CARD.exists():
        raise SystemExit(f"Missing required source: {CARD}")
    if not TAB.exists():
        raise SystemExit(f"Missing required source: {TAB}")
    if not REPLAY.exists():
        raise SystemExit(f"Missing required source: {REPLAY}")

    card = pd.read_csv(CARD, dtype=str, keep_default_na=False, low_memory=False)
    tab = pd.read_csv(TAB, dtype=str, keep_default_na=False, low_memory=False)
    replay = pd.read_csv(REPLAY, dtype=str, keep_default_na=False, low_memory=False)

    card["race_date_key"] = card["race_date"].map(clean).str[:10]
    card["track_key"] = card["track"].map(norm_track)
    card["race_no_key"] = card["race_no"].map(race_no_int)
    card["horse_key_norm"] = card["horse_key"].map(clean)
    card.loc[card["horse_key_norm"] == "", "horse_key_norm"] = card.loc[card["horse_key_norm"] == "", "horse"].map(horse_key)

    card = card[
        (card["race_date_key"] == TODAY)
        & (card["track_key"].isin(SOURCE_TRACKS))
        & card["race_no_key"].gt(0)
    ].copy()
    if card.empty:
        raise SystemExit(f"No today rows found in race_card_report.csv for {TODAY} {DISPLAY_TRACK}")

    tab["date_key"] = tab["meeting_date"].map(clean).str[:10]
    tab["race_no_key"] = tab["race_no"].map(race_no_int)
    tab["horse_key_norm"] = tab["horse_key"].map(clean)
    tab_lookup: dict[tuple[str, int, str], dict[str, str]] = {}
    for row in tab.to_dict("records"):
        tab_lookup[(clean(row.get("date_key")), int(row.get("race_no_key") or 0), clean(row.get("horse_key_norm")))] = row

    replay["race_date_key"] = replay["race_date"].map(clean).str[:10]
    replay["track_key"] = replay["track"].map(canonical_track)
    replay["race_no_key"] = replay["race_no"].map(race_no_int)
    replay["horse_key_norm"] = replay["horse_key"].map(clean)
    replay["probability_num"] = replay["V6_1_RESEARCH_probability"].map(num)
    replay = replay[
        (replay["race_date_key"] == TODAY)
        & (replay["track_key"] == DISPLAY_TRACK)
        & replay["race_no_key"].gt(0)
    ].copy()

    replay_lookup = {
        (row["race_date_key"], row["track_key"], int(row["race_no_key"]), row["horse_key_norm"]): row
        for row in replay.to_dict("records")
    }

    rows: list[dict[str, object]] = []
    for row in card.to_dict("records"):
        race_date = row["race_date_key"]
        track = canonical_track(row["track"])
        race_no = int(row["race_no_key"])
        hk = clean(row.get("horse_key_norm"))
        race_key = f"{race_date}_{track}_R{race_no}"

        tab_row = tab_lookup.get((race_date, race_no, hk), {})
        tab_status = clean(tab_row.get("tab_fixed_betting_status")).upper()
        scratched = (
            clean(row.get("is_scratched")).upper() in {"1", "TRUE", "YES"}
            or tab_status == "LATESCRATCHED"
            or "SCRATCH" in tab_status
        )
        raw_fair_price = num(row.get("rated_price"))
        live_price = num(tab_row.get("tab_fixed_win")) or num(row.get("market_price")) or num(row.get("fixed_odds"))
        replay_row = replay_lookup.get((race_date, track, race_no, hk), {})
        replay_prob = num(replay_row.get("probability_num"))
        rows.append(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "race_key": race_key,
                "horse": clean(row.get("horse")),
                "horse_key": hk,
                "scratched": scratched,
                "raw_fair_price": raw_fair_price,
                "live_price": live_price,
                "replay_probability": replay_prob,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise SystemExit("No audit rows were built.")

    audit_rows: list[dict[str, object]] = []
    for race_key, group in frame.groupby("race_key", sort=True):
        group = group.copy()
        raw_prob = group["raw_fair_price"].apply(implied_probability)
        group["raw_probability"] = raw_prob

        active_mask = (~group["scratched"]) & group["raw_fair_price"].notna() & group["raw_fair_price"].gt(0)
        scratched_mask = group["scratched"]

        raw_full_prob_sum = float(group["raw_probability"].sum())
        raw_active_prob_sum = float(group.loc[active_mask, "raw_probability"].sum())
        renorm_factor = (1.0 / raw_active_prob_sum) if raw_active_prob_sum > 0 else math.nan

        group["renorm_probability"] = 0.0
        if raw_active_prob_sum > 0:
            group.loc[active_mask, "renorm_probability"] = group.loc[active_mask, "raw_probability"] / raw_active_prob_sum

        group["renorm_fair_price"] = pd.NA
        group.loc[active_mask, "renorm_fair_price"] = group.loc[active_mask, "renorm_probability"].apply(
            lambda value: round(1.0 / value, 4) if value and value > 0 else pd.NA
        )

        group["edge_before"] = group.apply(lambda row: edge_pct(row["live_price"], row["raw_fair_price"]), axis=1)
        group["edge_after"] = group.apply(
            lambda row: edge_pct(row["live_price"], num(row["renorm_fair_price"])),
            axis=1,
        )

        group["decision_before"] = group.apply(
            lambda row: decision_from_edge(row["live_price"], row["edge_before"], bool(row["scratched"])),
            axis=1,
        )
        group["decision_after"] = group.apply(
            lambda row: decision_from_edge(row["live_price"], row["edge_after"], bool(row["scratched"])),
            axis=1,
        )

        changed_mask = active_mask & group["renorm_fair_price"].notna()
        fair_deltas = []
        for _, row in group.loc[changed_mask, ["raw_fair_price", "renorm_fair_price"]].iterrows():
            before = num(row["raw_fair_price"])
            after = num(row["renorm_fair_price"])
            if before is not None and after is not None:
                fair_deltas.append(abs(after - before))

        replay_prob_sum = float(group["replay_probability"].fillna(0).sum())
        overlay_before = int(((group["edge_before"].fillna(-999999) > 0) & active_mask).sum())
        overlay_after = int(((group["edge_after"].fillna(-999999) > 0) & active_mask).sum())
        watch_before = int(((group["decision_before"] == "WATCH") & active_mask).sum())
        watch_after = int(((group["decision_after"] == "WATCH") & active_mask).sum())
        lean_before = int(((group["decision_before"] == "LEAN") & active_mask).sum())
        lean_after = int(((group["decision_after"] == "LEAN") & active_mask).sum())
        pass_before = int(((group["decision_before"] == "PASS") & active_mask).sum())
        pass_after = int(((group["decision_after"] == "PASS") & active_mask).sum())

        audit_rows.append(
            {
                "race_date": clean(group["race_date"].iloc[0]),
                "track": clean(group["track"].iloc[0]),
                "race_no": int(group["race_no"].iloc[0]),
                "race_key": race_key,
                "total_rows": int(len(group)),
                "scratched_runners_removed": int(scratched_mask.sum()),
                "active_runners_after": int(active_mask.sum()),
                "raw_full_field_probability_pct": round(raw_full_prob_sum * 100.0, 2),
                "active_probability_before_pct": round(raw_active_prob_sum * 100.0, 2),
                "probability_after_pct": round(float(group["renorm_probability"].sum()) * 100.0, 2),
                "v6_1_probability_after_pct": round(replay_prob_sum * 100.0, 2),
                "probability_leak_pct": round((1.0 - raw_active_prob_sum) * 100.0, 2),
                "scratched_rows_with_fair_price_before": int((scratched_mask & group["raw_fair_price"].notna()).sum()),
                "scratched_rows_with_live_price": int((scratched_mask & group["live_price"].notna()).sum()),
                "fair_price_changed_runners": int(changed_mask.sum()),
                "avg_abs_fair_price_delta": round(sum(fair_deltas) / len(fair_deltas), 4) if fair_deltas else 0.0,
                "max_abs_fair_price_delta": round(max(fair_deltas), 4) if fair_deltas else 0.0,
                "overlay_rows_before": overlay_before,
                "overlay_rows_after": overlay_after,
                "overlay_rows_delta": overlay_after - overlay_before,
                "watch_rows_before": watch_before,
                "watch_rows_after": watch_after,
                "lean_rows_before": lean_before,
                "lean_rows_after": lean_after,
                "pass_rows_before": pass_before,
                "pass_rows_after": pass_after,
                "probability_bug_confirmed": "YES" if scratched_mask.any() and raw_active_prob_sum < 0.995 else "NO",
            }
        )

    audit = pd.DataFrame(audit_rows).sort_values(["race_date", "track", "race_no"]).reset_index(drop=True)
    audit.to_csv(OUT, index=False)

    races_with_scratches = int((audit["scratched_runners_removed"] > 0).sum())
    races_with_probability_leak = int((audit["probability_bug_confirmed"] == "YES").sum())
    upstream_normalised_races = int((audit["v6_1_probability_after_pct"].between(99.5, 100.5)).sum())
    verdict = (
        "SCRATCH_PROBABILITY_BUG_CONFIRMED_IN_LIVE_DISPLAY_PIPELINE"
        if races_with_probability_leak > 0
        else "NO_SCRATCH_PROBABILITY_BUG_FOUND"
    )

    summary = pd.DataFrame(
        [
            ("status", "COMPLETE"),
            ("today", TODAY),
            ("track", DISPLAY_TRACK),
            ("races_audited", int(len(audit))),
            ("rows_audited", int(len(frame))),
            ("scratched_rows", int(frame["scratched"].sum())),
            ("races_with_scratches", races_with_scratches),
            ("races_with_probability_leak", races_with_probability_leak),
            ("avg_active_probability_before_pct", round(float(audit["active_probability_before_pct"].mean()), 2)),
            ("min_active_probability_before_pct", round(float(audit["active_probability_before_pct"].min()), 2)),
            ("max_active_probability_before_pct", round(float(audit["active_probability_before_pct"].max()), 2)),
            ("avg_probability_leak_pct", round(float(audit["probability_leak_pct"].mean()), 2)),
            ("max_probability_leak_pct", round(float(audit["probability_leak_pct"].max()), 2)),
            ("upstream_v6_1_normalised_races", upstream_normalised_races),
            ("downstream_scratched_rows_with_fair_price", int(audit["scratched_rows_with_fair_price_before"].sum())),
            ("overlay_rows_before", int(audit["overlay_rows_before"].sum())),
            ("overlay_rows_after", int(audit["overlay_rows_after"].sum())),
            ("overlay_rows_delta", int(audit["overlay_rows_delta"].sum())),
            ("watch_rows_before", int(audit["watch_rows_before"].sum())),
            ("watch_rows_after", int(audit["watch_rows_after"].sum())),
            ("lean_rows_before", int(audit["lean_rows_before"].sum())),
            ("lean_rows_after", int(audit["lean_rows_after"].sum())),
            ("pass_rows_before", int(audit["pass_rows_before"].sum())),
            ("pass_rows_after", int(audit["pass_rows_after"].sum())),
            ("verdict", verdict),
        ],
        columns=["metric", "value"],
    )
    summary.to_csv(SUMMARY, index=False)

    print("[PROBABILITY_SCRATCH_AUDIT_V1] COMPLETE")
    print(f"races_audited={len(audit)}")
    print(f"scratched_rows={int(frame['scratched'].sum())}")
    print(f"races_with_probability_leak={races_with_probability_leak}")
    print(f"avg_active_probability_before_pct={round(float(audit['active_probability_before_pct'].mean()), 2)}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")


if __name__ == "__main__":
    main()
