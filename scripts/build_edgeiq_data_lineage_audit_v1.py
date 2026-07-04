import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FILES = {
    "live_runner_board": DATA / "edgeiq_live_runner_board_v1.csv",
    "v8": DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv",
    "bet_quality": DATA / "edgeiq_live_bet_quality_v1_1.csv",
    "intelligence_score": DATA / "edgeiq_live_intelligence_score_v1.csv",
    "results": DATA / "edgeiq_racingcom_results_warehouse_v1.csv",
    "race_timeline": DATA / "edgeiq_live_race_timeline_v1.csv",
    "results_review": DATA / "edgeiq_results_review_v1.csv",
    "active_selector": DATA / "edgeiq_active_race_selector.csv",
}

OUT_DETAIL = DATA / "edgeiq_data_lineage_audit_v1.csv"
OUT_JOIN = DATA / "edgeiq_data_lineage_join_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_data_lineage_audit_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_data_lineage_audit_v1.json"


def read_csv(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def clean(x):
    return str(x or "").strip()


def key_text(x):
    return "".join(ch for ch in clean(x).upper() if ch.isalnum())


def pick(row, cols):
    for c in cols:
        if c in row.index and clean(row.get(c)):
            return clean(row.get(c))
    return ""


def race_key(row):
    d = pick(row, ["race_date", "meeting_date", "date"])
    t = pick(row, ["track", "meeting_name", "venue"])
    rn = pick(row, ["race_no", "raceNo", "race_number", "join_race_no"])
    return f"{d}|{key_text(t)}|{clean(rn)}"


def runner_key(row):
    h = pick(row, ["horse", "horseName", "horse_name", "runner", "horse_key", "join_horse"])
    return f"{race_key(row)}|{key_text(h)}"


def non_blank(df, col):
    if df.empty or col not in df.columns:
        return 0
    return int((df[col].astype(str).str.strip() != "").sum())


def col_exists(df, col):
    return "YES" if not df.empty and col in df.columns else "NO"


def main():
    loaded = {name: read_csv(path) for name, path in FILES.items()}

    detail_rows = []

    key_columns = [
        "race_date", "meeting_date", "track", "race_no", "horse", "horseName",
        "fair_price", "v3_probability", "live_price", "edge_pct",
        "v8_candidate_price_display", "brc_match_level_v8",
        "bet_quality_score_v1_1", "bet_quality_grade_v1_1",
        "intelligence_score_v1", "intelligence_band_v1",
        "finishPosition", "sp", "raceTime",
    ]

    for name, df in loaded.items():
        path = FILES[name]
        race_keys = set()
        runner_keys = set()

        if not df.empty:
            for _, r in df.iterrows():
                rk = race_key(r)
                uk = runner_key(r)
                if rk.strip("|"):
                    race_keys.add(rk)
                if uk.strip("|"):
                    runner_keys.add(uk)

        row = {
            "source_name": name,
            "path": str(path),
            "exists": "YES" if path.exists() else "NO",
            "rows": int(len(df)),
            "columns": int(len(df.columns)) if not df.empty else 0,
            "unique_race_keys": len(race_keys),
            "unique_runner_keys": len(runner_keys),
            "min_date": "",
            "max_date": "",
        }

        date_col = None
        for c in ["race_date", "meeting_date", "date"]:
            if c in df.columns:
                date_col = c
                break

        if date_col:
            vals = df[date_col].astype(str).str.strip()
            vals = vals[vals != ""]
            if len(vals):
                row["min_date"] = vals.min()
                row["max_date"] = vals.max()

        for c in key_columns:
            row[f"has_{c}"] = col_exists(df, c)
            row[f"nonblank_{c}"] = non_blank(df, c)

        detail_rows.append(row)

    detail = pd.DataFrame(detail_rows)
    detail.to_csv(OUT_DETAIL, index=False)

    join_rows = []

    base_pairs = [
        ("live_runner_board", "v8"),
        ("live_runner_board", "bet_quality"),
        ("live_runner_board", "intelligence_score"),
        ("results", "live_runner_board"),
        ("results", "v8"),
        ("results", "bet_quality"),
        ("results_review", "results"),
    ]

    key_sets = {}

    for name, df in loaded.items():
        race_set = set()
        runner_set = set()
        if not df.empty:
            for _, r in df.iterrows():
                race_set.add(race_key(r))
                runner_set.add(runner_key(r))
        key_sets[name] = {"race": race_set, "runner": runner_set}

    for left, right in base_pairs:
        l_runner = key_sets[left]["runner"]
        r_runner = key_sets[right]["runner"]
        l_race = key_sets[left]["race"]
        r_race = key_sets[right]["race"]

        runner_matches = len(l_runner & r_runner)
        race_matches = len(l_race & r_race)

        join_rows.append(
            {
                "left_source": left,
                "right_source": right,
                "left_runner_keys": len(l_runner),
                "right_runner_keys": len(r_runner),
                "runner_key_matches": runner_matches,
                "runner_match_pct_of_left": round((runner_matches / len(l_runner)) * 100, 4) if l_runner else 0,
                "left_race_keys": len(l_race),
                "right_race_keys": len(r_race),
                "race_key_matches": race_matches,
                "race_match_pct_of_left": round((race_matches / len(l_race)) * 100, 4) if l_race else 0,
            }
        )

    join = pd.DataFrame(join_rows)
    join.to_csv(OUT_JOIN, index=False)

    summary = {
        "status": "COMPLETE",
        "sources_checked": len(FILES),
        "live_runner_rows": int(len(loaded["live_runner_board"])),
        "results_rows": int(len(loaded["results"])),
        "results_max_date": str(detail.loc[detail["source_name"] == "results", "max_date"].iloc[0]) if len(detail) else "",
        "live_v8_runner_matches": int(join[(join.left_source == "live_runner_board") & (join.right_source == "v8")]["runner_key_matches"].iloc[0]),
        "live_bet_quality_runner_matches": int(join[(join.left_source == "live_runner_board") & (join.right_source == "bet_quality")]["runner_key_matches"].iloc[0]),
        "results_live_runner_matches": int(join[(join.left_source == "results") & (join.right_source == "live_runner_board")]["runner_key_matches"].iloc[0]),
        "verdict": "DATA_LINEAGE_AUDIT_V1_COMPLETE",
    }

    pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[DATA_LINEAGE_AUDIT_V1] COMPLETE")
    for k, v in summary.items():
        print(f"{k}={v}")
    print(f"wrote={OUT_DETAIL}")
    print(f"joins={OUT_JOIN}")


if __name__ == "__main__":
    main()
