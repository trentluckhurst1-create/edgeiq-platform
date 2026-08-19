import pandas as pd
import re
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE_FILE = DATA / "edgeiq_live_runner_board_v1.csv"
STYLE_FILE = DATA / "edgeiq_runner_style_profile_v1.csv"

OUT_FILE = DATA / "edgeiq_live_runner_style_v1.csv"
SUMMARY_FILE = DATA / "edgeiq_live_runner_style_v1_summary.csv"

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_horse(v):
    s = txt(v).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    s = re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", s)
    return s

def canon_track(v):
    return re.sub(r"[^A-Z0-9]", "", txt(v).upper())

def runner_comment(r):
    style = txt(r.get("dominant_run_style"))
    movement = txt(r.get("movement_profile"))
    conf = txt(r.get("style_confidence"))
    starts = txt(r.get("starts"))

    if not style or style == "UNKNOWN":
        return "No reliable historical run-style profile found."

    parts = []
    parts.append(f"Historical profile: {style}.")
    parts.append(f"Based on {starts} historical runs.")
    parts.append(f"Movement profile: {movement}.")
    parts.append(f"Style confidence: {conf}.")
    return " ".join(parts)

def main():
    if not LIVE_FILE.exists():
        raise FileNotFoundError(LIVE_FILE)
    if not STYLE_FILE.exists():
        raise FileNotFoundError(STYLE_FILE)

    live = pd.read_csv(LIVE_FILE, dtype=str).fillna("")
    style = pd.read_csv(STYLE_FILE, dtype=str).fillna("")

    live["_horse_key"] = live.apply(
        lambda r: canon_horse(r.get("horse_canon") or r.get("horse")),
        axis=1
    )
    live["_track_key"] = live["track"].map(canon_track)
    live["_race_no"] = live["race_no"].map(txt)

    style["_horse_key"] = style["horse_key"].map(canon_horse)

    keep_cols = [
        "_horse_key",
        "starts",
        "dominant_run_style",
        "movement_profile",
        "style_confidence",
        "leader_pct",
        "onpace_pct",
        "midfield_pct",
        "backmarker_pct",
        "avg_pos800",
        "avg_pos400",
        "avg_gain_800_400",
        "leader_runs",
        "onpace_runs",
        "midfield_runs",
        "backmarker_runs",
        "improver_pct",
        "fader_pct",
        "holds_position_pct",
    ]

    style_keep = style[[c for c in keep_cols if c in style.columns]].drop_duplicates("_horse_key", keep="first")

    out = live.merge(
        style_keep,
        on="_horse_key",
        how="left"
    )

    for c in [
        "starts",
        "dominant_run_style",
        "movement_profile",
        "style_confidence",
        "leader_pct",
        "onpace_pct",
        "midfield_pct",
        "backmarker_pct",
        "avg_pos800",
        "avg_pos400",
        "avg_gain_800_400",
        "leader_runs",
        "onpace_runs",
        "midfield_runs",
        "backmarker_runs",
        "improver_pct",
        "fader_pct",
        "holds_position_pct",
    ]:
        if c not in out.columns:
            out[c] = ""
        out[c] = out[c].fillna("")

    out["runner_style_match_status"] = out["dominant_run_style"].apply(
        lambda x: "MATCHED" if txt(x) else "NO_HISTORICAL_STYLE"
    )

    out["runner_style_comment"] = out.apply(runner_comment, axis=1)

    final = pd.DataFrame({
        "race_date": out["race_date"],
        "track": out["track"],
        "race_no": out["race_no"],
        "horse_no": out.get("horse_no", ""),
        "horse": out["horse"],
        "horse_canon": out.get("horse_canon", out["_horse_key"]),
        "horse_key": out["_horse_key"],
        "barrier": out.get("barrier", ""),
        "distance": out.get("distance", ""),
        "jockey": out.get("jockey", ""),
        "trainer": out.get("trainer", ""),
        "live_price": out.get("live_price", ""),
        "fair_price": out.get("fair_price", ""),
        "edge_pct": out.get("edge_pct", ""),
        "starts": out["starts"],
        "dominant_run_style": out["dominant_run_style"],
        "movement_profile": out["movement_profile"],
        "style_confidence": out["style_confidence"],
        "leader_pct": out["leader_pct"],
        "onpace_pct": out["onpace_pct"],
        "midfield_pct": out["midfield_pct"],
        "backmarker_pct": out["backmarker_pct"],
        "leader_runs": out["leader_runs"],
        "onpace_runs": out["onpace_runs"],
        "midfield_runs": out["midfield_runs"],
        "backmarker_runs": out["backmarker_runs"],
        "avg_pos800": out["avg_pos800"],
        "avg_pos400": out["avg_pos400"],
        "avg_gain_800_400": out["avg_gain_800_400"],
        "improver_pct": out["improver_pct"],
        "fader_pct": out["fader_pct"],
        "holds_position_pct": out["holds_position_pct"],
        "runner_style_match_status": out["runner_style_match_status"],
        "runner_style_comment": out["runner_style_comment"],
    })

    final = final.sort_values(["track", "race_no", "horse_no", "horse"])
    final.to_csv(OUT_FILE, index=False)

    summary = pd.DataFrame([
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "live_rows", "value": len(live)},
        {"metric": "style_profile_rows", "value": len(style)},
        {"metric": "output_rows", "value": len(final)},
        {"metric": "matched_rows", "value": int(final["runner_style_match_status"].eq("MATCHED").sum())},
        {"metric": "unmatched_rows", "value": int(final["runner_style_match_status"].eq("NO_HISTORICAL_STYLE").sum())},
        {"metric": "high_confidence_rows", "value": int(final["style_confidence"].eq("HIGH").sum())},
        {"metric": "medium_confidence_rows", "value": int(final["style_confidence"].eq("MEDIUM").sum())},
        {"metric": "low_confidence_rows", "value": int(final["style_confidence"].eq("LOW").sum())},
        {"metric": "very_low_confidence_rows", "value": int(final["style_confidence"].eq("VERY_LOW").sum())},
        {"metric": "leader_rows", "value": int(final["dominant_run_style"].eq("LEADER").sum())},
        {"metric": "onpace_rows", "value": int(final["dominant_run_style"].eq("ON_PACE").sum())},
        {"metric": "midfield_rows", "value": int(final["dominant_run_style"].eq("MIDFIELD").sum())},
        {"metric": "backmarker_rows", "value": int(final["dominant_run_style"].eq("BACKMARKER").sum())},
        {"metric": "output", "value": OUT_FILE.name},
    ])

    summary.to_csv(SUMMARY_FILE, index=False)

    print("[LIVE_RUNNER_STYLE_V1] COMPLETE")
    print(f"live_rows={len(live)}")
    print(f"matched_rows={int(final['runner_style_match_status'].eq('MATCHED').sum())}")
    print(f"unmatched_rows={int(final['runner_style_match_status'].eq('NO_HISTORICAL_STYLE').sum())}")
    print(f"wrote={OUT_FILE}")

if __name__ == "__main__":
    main()
