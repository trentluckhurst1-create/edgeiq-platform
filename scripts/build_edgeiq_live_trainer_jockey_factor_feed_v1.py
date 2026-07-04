from pathlib import Path
import json
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
TRAINER = DATA / "edgeiq_trainer_factor_v1.csv"
JOCKEY = DATA / "edgeiq_jockey_factor_v1.csv"
COMBO = DATA / "edgeiq_trainer_jockey_combo_factor_v1.csv"

OUT = DATA / "edgeiq_live_trainer_jockey_factor_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_trainer_jockey_factor_feed_v1_summary.csv"
OUT_UNMATCHED = DATA / "edgeiq_live_trainer_jockey_factor_feed_v1_unmatched.csv"
OUT_JSON = DATA / "edgeiq_live_trainer_jockey_factor_feed_v1.json"


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def clean_letters(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))


def strip_rider_claims(x):
    s = norm(x)
    s = re.sub(r"\(A[0-9.]*\/?[0-9A-Z.]*KG?\)", "", s)
    s = re.sub(r"\(A[0-9.]*\)", "", s)
    s = re.sub(r"\([^)]+\)", "", s)
    s = s.replace("MS ", "").replace("MR ", "").replace("MRS ", "").replace("MISS ", "")
    return " ".join(s.split())


def name_variants(name):
    raw = strip_rider_claims(name)
    parts = [p for p in re.split(r"\s+", raw) if p]

    variants = set()
    variants.add(clean_letters(raw))

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        variants.add(clean_letters(first[0] + last))
        variants.add(clean_letters(last))
        variants.add(clean_letters(first + last))

    if len(parts) >= 3:
        first = parts[0]
        middle = parts[1]
        last = parts[-1]
        variants.add(clean_letters(first[0] + middle[0] + last))

    return [v for v in variants if v]


def build_lookup(factor, key_col):
    lookup = {}
    surname_counts = {}

    for _, r in factor.iterrows():
        key = clean_letters(r[key_col])
        name_col = None

        if "trainer" in factor.columns:
            name_col = "trainer"
        elif "jockey" in factor.columns:
            name_col = "jockey"
        elif "trainer_jockey" in factor.columns:
            name_col = "trainer_jockey"

        lookup[key] = r.to_dict()

        if name_col and "|" not in key:
            name = norm(r.get(name_col, ""))
            raw_parts = re.split(r"[^A-Z]+", name)
            raw_parts = [p for p in raw_parts if p]
            if raw_parts:
                surname = raw_parts[-1]
                surname_counts[surname] = surname_counts.get(surname, 0) + 1

    return lookup, surname_counts


def match_person(name, lookup, surname_counts):
    variants = name_variants(name)

    for v in variants:
        if v in lookup:
            return lookup[v], "EXACT_OR_INITIAL_KEY"

    # Last-name fallback only when unique in factor table.
    raw = strip_rider_claims(name)
    parts = [p for p in re.split(r"\s+", raw) if p]
    if parts:
        surname = clean_letters(parts[-1])
        if surname_counts.get(surname, 0) == 1:
            for k, row in lookup.items():
                if k.endswith(surname):
                    return row, "UNIQUE_SURNAME_FALLBACK"

    return None, "UNMATCHED"


def combo_key_from_rows(trainer_row, jockey_row):
    if not trainer_row or not jockey_row:
        return ""
    tk = clean_letters(trainer_row.get("trainer_key", ""))
    jk = clean_letters(jockey_row.get("jockey_key", ""))
    if not tk or not jk:
        return ""
    return tk + "|" + jk


def main():
    required_files = [LIVE, TRAINER, JOCKEY, COMBO]
    missing = [str(f) for f in required_files if not f.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    live = pd.read_csv(LIVE, low_memory=False)
    trainer = pd.read_csv(TRAINER, low_memory=False)
    jockey = pd.read_csv(JOCKEY, low_memory=False)
    combo = pd.read_csv(COMBO, low_memory=False)

    required_live_cols = ["track", "race_no", "horse", "trainer", "jockey"]
    missing_cols = [c for c in required_live_cols if c not in live.columns]
    if missing_cols:
        raise ValueError(f"Live board missing required columns: {missing_cols}")

    trainer_lookup, trainer_surname_counts = build_lookup(trainer, "trainer_key")
    jockey_lookup, jockey_surname_counts = build_lookup(jockey, "jockey_key")

    combo_lookup = {}
    for _, r in combo.iterrows():
        combo_lookup[norm(r["trainer_jockey_key"]).replace(" ", "")] = r.to_dict()

    rows = []

    for _, r in live.iterrows():
        base = r.to_dict()

        trainer_row, trainer_method = match_person(r.get("trainer", ""), trainer_lookup, trainer_surname_counts)
        jockey_row, jockey_method = match_person(r.get("jockey", ""), jockey_lookup, jockey_surname_counts)

        combo_key = combo_key_from_rows(trainer_row, jockey_row)
        combo_row = combo_lookup.get(combo_key)

        trainer_score = float(trainer_row.get("trainer_factor_score_v1", 0)) if trainer_row else 0.0
        jockey_score = float(jockey_row.get("jockey_factor_score_v1", 0)) if jockey_row else 0.0
        combo_score = float(combo_row.get("combo_factor_score_v1", 0)) if combo_row else 0.0

        blend = round((trainer_score * 0.35) + (jockey_score * 0.45) + (combo_score * 0.20), 3)

        if blend >= 1.25:
            blend_band = "ELITE"
        elif blend >= 0.50:
            blend_band = "POSITIVE"
        elif blend <= -1.25:
            blend_band = "POOR"
        elif blend <= -0.50:
            blend_band = "NEGATIVE"
        else:
            blend_band = "NEUTRAL"

        base.update({
            "trainer_factor_matched_v1": "YES" if trainer_row else "NO",
            "jockey_factor_matched_v1": "YES" if jockey_row else "NO",
            "combo_factor_matched_v1": "YES" if combo_row else "NO",
            "trainer_match_method_v1": trainer_method,
            "jockey_match_method_v1": jockey_method,

            "trainer_factor_band_v1": trainer_row.get("trainer_factor_band_v1", "UNKNOWN") if trainer_row else "UNKNOWN",
            "trainer_factor_score_v1": trainer_score,
            "trainer_factor_starts_v1": trainer_row.get("trainer_starts_v1", "") if trainer_row else "",
            "trainer_win_pct_v1": trainer_row.get("trainer_win_pct_v1", "") if trainer_row else "",
            "trainer_place_pct_v1": trainer_row.get("trainer_place_pct_v1", "") if trainer_row else "",

            "jockey_factor_band_v1": jockey_row.get("jockey_factor_band_v1", "UNKNOWN") if jockey_row else "UNKNOWN",
            "jockey_factor_score_v1": jockey_score,
            "jockey_factor_starts_v1": jockey_row.get("jockey_starts_v1", "") if jockey_row else "",
            "jockey_win_pct_v1": jockey_row.get("jockey_win_pct_v1", "") if jockey_row else "",
            "jockey_place_pct_v1": jockey_row.get("jockey_place_pct_v1", "") if jockey_row else "",

            "combo_factor_band_v1": combo_row.get("combo_factor_band_v1", "UNKNOWN") if combo_row else "UNKNOWN",
            "combo_factor_score_v1": combo_score,
            "combo_factor_starts_v1": combo_row.get("combo_starts_v1", "") if combo_row else "",
            "combo_win_pct_v1": combo_row.get("combo_win_pct_v1", "") if combo_row else "",
            "combo_place_pct_v1": combo_row.get("combo_place_pct_v1", "") if combo_row else "",

            "trainer_jockey_blend_score_v1": blend,
            "trainer_jockey_blend_band_v1": blend_band,
            "tj_edge_label_v1": "TJ Edge: " + blend_band,
        })

        if trainer_row and jockey_row and combo_row:
            verdict = "COMPLETE"
        elif trainer_row and jockey_row:
            verdict = "TRAINER_JOCKEY_ONLY"
        elif trainer_row or jockey_row:
            verdict = "PARTIAL"
        else:
            verdict = "UNMATCHED"

        base["tj_factor_verdict_v1"] = verdict
        rows.append(base)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    unmatched = out[out["tj_factor_verdict_v1"] != "COMPLETE"].copy()
    unmatched.to_csv(OUT_UNMATCHED, index=False)

    summary = pd.DataFrame([
        ["source_file_used", LIVE.name],
        ["live_rows", len(out)],
        ["trainer_matched", int((out["trainer_factor_matched_v1"] == "YES").sum())],
        ["trainer_match_pct", round((out["trainer_factor_matched_v1"] == "YES").mean() * 100, 2)],
        ["jockey_matched", int((out["jockey_factor_matched_v1"] == "YES").sum())],
        ["jockey_match_pct", round((out["jockey_factor_matched_v1"] == "YES").mean() * 100, 2)],
        ["combo_matched", int((out["combo_factor_matched_v1"] == "YES").sum())],
        ["combo_match_pct", round((out["combo_factor_matched_v1"] == "YES").mean() * 100, 2)],
        ["complete_rows", int((out["tj_factor_verdict_v1"] == "COMPLETE").sum())],
        ["partial_or_unmatched_rows", int((out["tj_factor_verdict_v1"] != "COMPLETE").sum())],
        ["observation_only", "YES"],
        ["price_or_execution_changed", "NO"],
    ], columns=["metric", "value"])

    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "source_file_used": str(LIVE),
        "live_rows": int(len(out)),
        "trainer_match_pct": round((out["trainer_factor_matched_v1"] == "YES").mean() * 100, 2),
        "jockey_match_pct": round((out["jockey_factor_matched_v1"] == "YES").mean() * 100, 2),
        "combo_match_pct": round((out["combo_factor_matched_v1"] == "YES").mean() * 100, 2),
        "complete_rows": int((out["tj_factor_verdict_v1"] == "COMPLETE").sum()),
        "partial_or_unmatched_rows": int((out["tj_factor_verdict_v1"] != "COMPLETE").sum()),
        "observation_only": True,
        "price_or_execution_changed": False,
        "outputs": {
            "feed": str(OUT),
            "summary": str(OUT_SUMMARY),
            "unmatched": str(OUT_UNMATCHED),
        },
    }, indent=2), encoding="utf-8")

    print("[LIVE_TRAINER_JOCKEY_FACTOR_FEED_V1] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
