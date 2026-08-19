from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

NO_HISTORY = DATA / "edgeiq_no_history_governance_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_all_v1.csv"
RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
STYLE_PROFILE = DATA / "edgeiq_runner_style_profile_v1.csv"

OUT = DATA / "edgeiq_no_history_forensic_audit_v1.csv"
SUMMARY = DATA / "edgeiq_no_history_forensic_audit_v1_summary.csv"
MATCHES = DATA / "edgeiq_no_history_forensic_audit_v1_possible_matches.csv"

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_horse(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def loose_horse(x):
    s = canon_horse(x)
    for suffix in ["NZ", "IRE", "GB", "USA", "FR", "JPN", "GER"]:
        if s.endswith(suffix) and len(s) > len(suffix) + 2:
            s = s[:-len(suffix)]
    return s

def norm_words(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(s.split())

def find_col(df, options):
    lower = {c.lower(): c for c in df.columns}
    for opt in options:
        if opt.lower() in lower:
            return lower[opt.lower()]
    return None

def add_keys(df, horse_col):
    df = df.copy()
    df["_horse_raw"] = df[horse_col].map(safe)
    df["_horse_canon"] = df[horse_col].map(canon_horse)
    df["_horse_loose"] = df[horse_col].map(loose_horse)
    df["_horse_words"] = df[horse_col].map(norm_words)
    return df

def classify(row):
    if row["profile_exact_match"]:
        return "HISTORY_FOUND_PROFILE_EXACT"
    if row["run_style_exact_match"]:
        return "HISTORY_FOUND_RUN_STYLE_EXACT"
    if row["results_exact_match"]:
        return "HISTORY_FOUND_RESULTS_EXACT"
    if row["profile_loose_match"]:
        return "HISTORY_FOUND_PROFILE_LOOSE"
    if row["run_style_loose_match"]:
        return "HISTORY_FOUND_RUN_STYLE_LOOSE"
    if row["results_loose_match"]:
        return "HISTORY_FOUND_RESULTS_LOOSE"
    if row["possible_word_match_count"] > 0:
        return "POSSIBLE_NAME_MATCH_REVIEW"
    return "GENUINE_NO_HISTORY_OR_UNMATCHED"

def main():
    if not NO_HISTORY.exists():
        raise FileNotFoundError(f"Missing {NO_HISTORY}")

    nohist = pd.read_csv(NO_HISTORY, dtype=str, low_memory=False)
    nohist.columns = [c.strip() for c in nohist.columns]
    nohist = nohist[nohist["no_history_flag"].astype(str).eq("True")].copy()
    nohist = add_keys(nohist, "horse")

    sources = {}

    if RESULTS.exists():
        results = pd.read_csv(RESULTS, dtype=str, low_memory=False)
        results.columns = [c.strip() for c in results.columns]
        horse_col = find_col(results, ["horse", "runner", "horse_name"])
        if horse_col:
            results = add_keys(results, horse_col)
            sources["results"] = results
        else:
            sources["results"] = pd.DataFrame()
    else:
        sources["results"] = pd.DataFrame()

    if RUN_STYLE.exists():
        rs = pd.read_csv(RUN_STYLE, dtype=str, low_memory=False)
        rs.columns = [c.strip() for c in rs.columns]
        horse_col = find_col(rs, ["horse", "runner", "horse_name"])
        if horse_col:
            rs = add_keys(rs, horse_col)
            sources["run_style"] = rs
        else:
            sources["run_style"] = pd.DataFrame()
    else:
        sources["run_style"] = pd.DataFrame()

    if STYLE_PROFILE.exists():
        prof = pd.read_csv(STYLE_PROFILE, dtype=str, low_memory=False)
        prof.columns = [c.strip() for c in prof.columns]
        horse_col = find_col(prof, ["horse", "runner", "horse_name"])
        if horse_col:
            prof = add_keys(prof, horse_col)
            sources["profile"] = prof
        else:
            sources["profile"] = pd.DataFrame()
    else:
        sources["profile"] = pd.DataFrame()

    lookup = {}
    for name, df in sources.items():
        if df.empty:
            lookup[name] = {
                "exact": set(),
                "loose": set(),
                "counts_exact": {},
                "counts_loose": {},
                "sample": {}
            }
            continue

        exact_counts = df["_horse_canon"].value_counts().to_dict()
        loose_counts = df["_horse_loose"].value_counts().to_dict()

        sample = (
            df.drop_duplicates("_horse_canon")
              .set_index("_horse_canon")["_horse_raw"]
              .to_dict()
        )

        lookup[name] = {
            "exact": set(exact_counts.keys()),
            "loose": set(loose_counts.keys()),
            "counts_exact": exact_counts,
            "counts_loose": loose_counts,
            "sample": sample
        }

    records = []
    possible = []

    all_word_index = []
    for source_name, df in sources.items():
        if df.empty:
            continue
        sample_cols = ["_horse_raw", "_horse_canon", "_horse_loose", "_horse_words"]
        for _, r in df[sample_cols].drop_duplicates("_horse_canon").iterrows():
            all_word_index.append({
                "source": source_name,
                "source_horse": r["_horse_raw"],
                "source_canon": r["_horse_canon"],
                "source_loose": r["_horse_loose"],
                "source_words": r["_horse_words"],
            })

    for _, r in nohist.iterrows():
        canon = r["_horse_canon"]
        loose = r["_horse_loose"]
        words = r["_horse_words"]

        results_exact = canon in lookup["results"]["exact"]
        results_loose = loose in lookup["results"]["loose"]
        rs_exact = canon in lookup["run_style"]["exact"]
        rs_loose = loose in lookup["run_style"]["loose"]
        prof_exact = canon in lookup["profile"]["exact"]
        prof_loose = loose in lookup["profile"]["loose"]

        word_matches = []
        if words:
            tokens = set(words.split())
            for item in all_word_index:
                src_tokens = set(item["source_words"].split())
                if not src_tokens:
                    continue
                overlap = len(tokens.intersection(src_tokens))
                if overlap >= max(1, min(2, len(tokens))):
                    if item["source_canon"] != canon and item["source_loose"] != loose:
                        word_matches.append(item)

        word_matches = word_matches[:10]

        row = {
            "race_date": safe(r.get("race_date")),
            "track": safe(r.get("track")),
            "race_no": safe(r.get("race_no")),
            "horse": safe(r.get("horse")),
            "horse_canon_forensic": canon,
            "horse_loose_forensic": loose,
            "market_price": safe(r.get("market_price")),
            "official_fair_price": safe(r.get("official_fair_price")),
            "display_fair_price_governed": safe(r.get("display_fair_price_governed")),
            "no_history_governance_band": safe(r.get("no_history_governance_band")),
            "results_exact_match": results_exact,
            "results_loose_match": results_loose,
            "results_exact_runs": lookup["results"]["counts_exact"].get(canon, 0),
            "results_loose_runs": lookup["results"]["counts_loose"].get(loose, 0),
            "run_style_exact_match": rs_exact,
            "run_style_loose_match": rs_loose,
            "run_style_exact_runs": lookup["run_style"]["counts_exact"].get(canon, 0),
            "run_style_loose_runs": lookup["run_style"]["counts_loose"].get(loose, 0),
            "profile_exact_match": prof_exact,
            "profile_loose_match": prof_loose,
            "profile_exact_rows": lookup["profile"]["counts_exact"].get(canon, 0),
            "profile_loose_rows": lookup["profile"]["counts_loose"].get(loose, 0),
            "possible_word_match_count": len(word_matches),
        }

        row["forensic_verdict"] = classify(row)

        records.append(row)

        for m in word_matches:
            possible.append({
                "track": row["track"],
                "race_no": row["race_no"],
                "no_history_horse": row["horse"],
                "no_history_canon": canon,
                "source": m["source"],
                "source_horse": m["source_horse"],
                "source_canon": m["source_canon"],
                "source_loose": m["source_loose"],
            })

    final = pd.DataFrame(records)
    final.to_csv(OUT, index=False)

    pd.DataFrame(possible).to_csv(MATCHES, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("no_history_rows", len(final)),
        ("results_exact_matches", int(final["results_exact_match"].eq(True).sum())),
        ("results_loose_matches", int(final["results_loose_match"].eq(True).sum())),
        ("run_style_exact_matches", int(final["run_style_exact_match"].eq(True).sum())),
        ("run_style_loose_matches", int(final["run_style_loose_match"].eq(True).sum())),
        ("profile_exact_matches", int(final["profile_exact_match"].eq(True).sum())),
        ("profile_loose_matches", int(final["profile_loose_match"].eq(True).sum())),
        ("possible_word_match_rows", int(final["possible_word_match_count"].gt(0).sum())),
        ("possible_match_rows_written", len(possible)),
    ]

    for k, v in final["forensic_verdict"].value_counts(dropna=False).to_dict().items():
        summary.append((f"verdict_{k}", v))

    pd.DataFrame(summary, columns=["metric", "value"]).to_csv(SUMMARY, index=False)

    print("[NO_HISTORY_FORENSIC_AUDIT_V1] COMPLETE")
    print(f"no_history_rows={len(final)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")
    print(f"possible_matches={MATCHES}")

if __name__ == "__main__":
    main()
