from pathlib import Path
import re
import json
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"
V8_UNMATCHED = DATA / "edgeiq_live_v8_candidate_display_feed_v1_unmatched.csv"
LIVE = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_SUMMARY = DATA / "edgeiq_live_v8_candidate_display_feed_v1_keyfix_summary.csv"
OUT_JSON = DATA / "edgeiq_live_v8_candidate_display_feed_v1_keyfix.json"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def clean(x):
    return str(x or "").strip()


def canon(x):
    s = clean(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s


def key(track, race_no, horse):
    return f"{canon(track)}|{clean(race_no)}|{canon(horse)}"


def race_key(race_date, track, race_no):
    return f"{clean(race_date)}_{canon(track)}_R{clean(race_no)}"


def runner_key(race_date, track, race_no, horse):
    return f"{race_key(race_date, track, race_no)}|{canon(horse)}"


def enrich(v8: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    if v8.empty:
        return v8

    live_map = {}

    if not live.empty:
        for _, r in live.iterrows():
            k = key(r.get("track"), r.get("race_no"), r.get("horse"))
            live_map[k] = {
                "race_date": clean(r.get("race_date")),
                "track": clean(r.get("track")),
                "race_no": clean(r.get("race_no")),
                "horse": clean(r.get("horse")),
                "horse_canon": canon(r.get("horse_canon") or r.get("horse")),
            }

    out = v8.copy()

    for c in [
        "race_date",
        "horse_canon",
        "horse_key",
        "race_key",
        "runner_key",
        "join_track",
        "join_race_no",
        "join_horse",
        "join_race",
    ]:
        if c not in out.columns:
            out[c] = ""

    matched = 0

    for idx, r in out.iterrows():
        k = key(r.get("track"), r.get("race_no"), r.get("horse"))
        m = live_map.get(k)

        if m:
            matched += 1
            rd = m["race_date"]
            tr = m["track"]
            rn = m["race_no"]
            h = m["horse"]
            hc = m["horse_canon"]
        else:
            rd = clean(r.get("race_date"))
            tr = clean(r.get("track"))
            rn = clean(r.get("race_no"))
            h = clean(r.get("horse"))
            hc = canon(h)

        out.at[idx, "race_date"] = rd
        out.at[idx, "track"] = tr
        out.at[idx, "race_no"] = rn
        out.at[idx, "horse"] = h
        out.at[idx, "horse_canon"] = hc
        out.at[idx, "horse_key"] = hc
        out.at[idx, "race_key"] = race_key(rd, tr, rn)
        out.at[idx, "runner_key"] = runner_key(rd, tr, rn, h)
        out.at[idx, "join_track"] = canon(tr)
        out.at[idx, "join_race_no"] = rn
        out.at[idx, "join_horse"] = hc
        out.at[idx, "join_race"] = race_key(rd, tr, rn)

    # Put key columns first for every downstream consumer.
    front = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_canon",
        "horse_key",
        "race_key",
        "runner_key",
        "join_track",
        "join_race_no",
        "join_horse",
        "join_race",
    ]

    cols = front + [c for c in out.columns if c not in front]
    out = out[cols]

    out.attrs["matched"] = matched
    return out


def main():
    v8 = read_csv(V8)
    live = read_csv(LIVE)

    if v8.empty:
        raise SystemExit("[V8_KEYFIX] ERROR missing or empty V8 feed")

    fixed = enrich(v8, live)
    fixed.to_csv(V8, index=False)

    if V8_UNMATCHED.exists():
        unmatched = read_csv(V8_UNMATCHED)
        if not unmatched.empty:
            enrich(unmatched, live).to_csv(V8_UNMATCHED, index=False)

    matched = int(fixed.attrs.get("matched", 0))
    summary = {
        "status": "COMPLETE",
        "rows": int(len(fixed)),
        "live_rows": int(len(live)),
        "live_matched_rows": matched,
        "race_date_nonblank": int((fixed["race_date"].astype(str).str.strip() != "").sum()),
        "race_key_nonblank": int((fixed["race_key"].astype(str).str.strip() != "").sum()),
        "runner_key_nonblank": int((fixed["runner_key"].astype(str).str.strip() != "").sum()),
        "verdict": "V8_CANONICAL_KEYS_FIXED",
    }

    pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[V8_KEYFIX] COMPLETE")
    for k, v in summary.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
