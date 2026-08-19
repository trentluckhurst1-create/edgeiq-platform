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

OUT = DATA / "edgeiq_live_trainer_jockey_factor_feed_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_live_trainer_jockey_factor_feed_v2_summary.csv"
OUT_UNMATCHED = DATA / "edgeiq_live_trainer_jockey_factor_feed_v2_unmatched.csv"
OUT_JSON = DATA / "edgeiq_live_trainer_jockey_factor_feed_v2.json"

# Live-name -> historical factor-key aliases, based on current match audit.
TRAINER_KEY_ALIASES = {
    "BENWILLJDHAYES": "BWWJDHAYES",
    "DANNYOBRIEN": "DTOBRIEN",
    "ANTHONYSAMFREEDMAN": "ASFREEDMAN",
    "MICKPRICEMICHAELKENTJNR": "MPRICEMKENTJNR",
    "MICHAELKENT": "MPRICEMKENTJNR",
    "PETERGMOODYKATHERINECOLEMAN": "PGMOODYKCOLEMAN",
    "ROBBIEGRIFFITHS": "RGRIFFITHS",
    "MATTHEWWILLIAMS": "MJWILLIAMS",
    "REECEGOODWIN": "RJGOODWIN",
    "AARONPURCELL": "APURCELL",
    "HELENBURNS": "HBURNS",
    "CONKELLY": "CKELLY",
    "RAHARNAMCDONALD": "RMCDONALD",
    "CAMERONTHOMPSON": "CTHOMPSON",
    "ANNJEANETTETINDALE": "AJTINDALE",
    "MICHAELHICKMOTT": "MHICKMOTT",
    "MARKWALKER": "MWALKER",
    "SUE MURPHY": "SMURPHY",
    "SUEMURPHY": "SMURPHY",
    "PAULGRAESSER": "PGRAESSER",
    "RICHARDWILSON": "RWILSON",
    "DAMIENHUNTER": "DHUNTER",
    "WAYNENICHOLS": "WNICHOLS",
    "SEANMOTT": "SMOTT",
    "RHYSARCHARD": "RARCHARD",
    "MICKBELL": "MBELL",
    "MATTHEWENRIGHT": "MENRIGHT",
    "BRYANMAHER": "BMAHER",
    "BELINDAOLOUGHLIN": "BOLOUGHLIN",
    "ANDREWCAMPBELL": "ACAMPBELL",
    "JORDYCOFFEY": "JCOFFEY",
    "HEIDISMITH": "HSMITH",
    "BILLCERCHI": "BCERCHI",
    "TOBYLAKE": "TLAKE",
    "PATCANNON": "PCANNON",
    "DAVIDOPREY": "DOPREY",
    "JASONCANNON": "JCANNON",
    "NICKRYAN": "NRYAN",
    "MATTHEWDALE": "MDALE",
    "JACKLAING": "JLAING",
}

JOCKEY_KEY_ALIASES = {
    "JACKHILL": "JDHILL",
    "JETTSTANLEY": "JSTANLEY",
    "ALANAKELLY": "AKKELLY",
    "MSALANAKELLY": "AKKELLY",
    "CHELSEATAYLOR": "CTAYLOR",
    "MSCHELSEATAYLOR": "CTAYLOR",
    "CHELSEATHOMPSON": "CTHOMPSON",
    "MSCHELSEATHOMPSON": "CTHOMPSON",
    "LUKECARTWRIGHT": "LCARTWRIGHT",
    "LOGANBATES": "LBATES",
    "JABEZJOHNSTONE": "JJOHNSTONE",
    "CASSIDYHILL": "CHILL",
    "MSCASSIDYHILL": "CHILL",
    "LOGANMCNEIL": "LMCNEIL",
    "ALICEKENNEDY": "AKENNEDY",
    "MSALICEKENNEDY": "AKENNEDY",
    "HOLLYDURNAN": "HDURNAN",
    "MSHOLLYDURNAN": "HDURNAN",
    "SHAYLEIGHINGELSE": "SINGELSE",
    "MSSHAYLEIGHINGELSE": "SINGELSE",
    "STACEYMETCALFE": "SMETCALFE",
    "MSSTACEYMETCALFE": "SMETCALFE",
    "YOKOOTA": "YOTA",
    "MSYOKOOTA": "YOTA",
}


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def clean_key(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))


def clean_person_name(x):
    s = norm(x)
    s = s.replace("(LATE ALT)", "")
    s = re.sub(r"\(A[0-9.]*\/?[0-9A-Z.]*KG?\)", "", s)
    s = re.sub(r"\(A[0-9.]*\)", "", s)
    s = re.sub(r"\([^)]+\)", "", s)
    s = s.replace("MS ", "").replace("MR ", "").replace("MRS ", "").replace("MISS ", "")
    s = s.replace(",", " ")
    return " ".join(s.split())


def name_variants(name):
    raw = clean_person_name(name)
    compact = clean_key(raw)
    parts = [p for p in raw.split(" ") if p]

    variants = set()
    if compact:
        variants.add(compact)

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        variants.add(clean_key(first[0] + last))
        variants.add(clean_key(first + last))

    if len(parts) >= 3:
        first = parts[0]
        middle = parts[1]
        last = parts[-1]
        variants.add(clean_key(first[0] + middle[0] + last))

    return [v for v in variants if v]


def build_person_lookup(df, key_col, name_col):
    lookup = {}
    surname_index = {}

    for _, row in df.iterrows():
        k = clean_key(row.get(key_col, ""))
        nm = clean_person_name(row.get(name_col, ""))

        if k:
            lookup[k] = row.to_dict()

        for v in name_variants(nm):
            lookup.setdefault(v, row.to_dict())

        parts = [p for p in nm.split(" ") if p]
        if parts:
            surname = clean_key(parts[-1])
            surname_index.setdefault(surname, set()).add(k)

    return lookup, surname_index


def match_entity(name, lookup, surname_index, aliases, key_col):
    variants = name_variants(name)

    for v in variants:
        alias_key = aliases.get(v)
        if alias_key and alias_key in lookup:
            return lookup[alias_key], "MANUAL_ALIAS"

    for v in variants:
        if v in lookup:
            return lookup[v], "EXACT_OR_VARIANT"

    raw = clean_person_name(name)
    parts = [p for p in raw.split(" ") if p]
    if parts:
        surname = clean_key(parts[-1])
        keys = surname_index.get(surname, set())
        if len(keys) == 1:
            only_key = list(keys)[0]
            if only_key in lookup:
                return lookup[only_key], "UNIQUE_SURNAME"

    return None, "UNMATCHED"


def combo_lookup_key(trainer_row, jockey_row):
    if not trainer_row or not jockey_row:
        return ""
    tk = clean_key(trainer_row.get("trainer_key", ""))
    jk = clean_key(jockey_row.get("jockey_key", ""))
    if not tk or not jk:
        return ""
    return tk + "|" + jk


def band_from_blend(score):
    if score >= 1.25:
        return "ELITE"
    if score >= 0.50:
        return "POSITIVE"
    if score <= -1.25:
        return "POOR"
    if score <= -0.50:
        return "NEGATIVE"
    return "NEUTRAL"


def main():
    for f in [LIVE, TRAINER, JOCKEY, COMBO]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required file: {f}")

    live = pd.read_csv(LIVE, low_memory=False)
    trainer = pd.read_csv(TRAINER, low_memory=False)
    jockey = pd.read_csv(JOCKEY, low_memory=False)
    combo = pd.read_csv(COMBO, low_memory=False)

    required_live_cols = ["track", "race_no", "horse", "trainer", "jockey"]
    missing_cols = [c for c in required_live_cols if c not in live.columns]
    if missing_cols:
        raise ValueError(f"Live board missing required columns: {missing_cols}")

    trainer_lookup, trainer_surname_index = build_person_lookup(trainer, "trainer_key", "trainer")
    jockey_lookup, jockey_surname_index = build_person_lookup(jockey, "jockey_key", "jockey")

    combo_lookup = {}
    for _, row in combo.iterrows():
        k = norm(row.get("trainer_jockey_key", "")).replace(" ", "")
        if k:
            combo_lookup[k] = row.to_dict()

    rows = []

    for _, r in live.iterrows():
        base = r.to_dict()

        trainer_row, trainer_method = match_entity(
            r.get("trainer", ""),
            trainer_lookup,
            trainer_surname_index,
            TRAINER_KEY_ALIASES,
            "trainer_key",
        )

        jockey_row, jockey_method = match_entity(
            r.get("jockey", ""),
            jockey_lookup,
            jockey_surname_index,
            JOCKEY_KEY_ALIASES,
            "jockey_key",
        )

        ck = combo_lookup_key(trainer_row, jockey_row)
        combo_row = combo_lookup.get(ck)

        trainer_score = float(trainer_row.get("trainer_factor_score_v1", 0)) if trainer_row else 0.0
        jockey_score = float(jockey_row.get("jockey_factor_score_v1", 0)) if jockey_row else 0.0
        combo_score = float(combo_row.get("combo_factor_score_v1", 0)) if combo_row else 0.0

        blend = round((trainer_score * 0.35) + (jockey_score * 0.45) + (combo_score * 0.20), 3)
        blend_band = band_from_blend(blend)

        base.update({
            "tj_v2_trainer_clean": clean_person_name(r.get("trainer", "")),
            "tj_v2_jockey_clean": clean_person_name(r.get("jockey", "")),

            "trainer_factor_matched_v2": "YES" if trainer_row else "NO",
            "jockey_factor_matched_v2": "YES" if jockey_row else "NO",
            "combo_factor_matched_v2": "YES" if combo_row else "NO",
            "trainer_match_method_v2": trainer_method,
            "jockey_match_method_v2": jockey_method,

            "trainer_factor_band_v2": trainer_row.get("trainer_factor_band_v1", "UNKNOWN") if trainer_row else "UNKNOWN",
            "trainer_factor_score_v2": trainer_score,
            "trainer_factor_starts_v2": trainer_row.get("trainer_starts_v1", "") if trainer_row else "",
            "trainer_win_pct_v2": trainer_row.get("trainer_win_pct_v1", "") if trainer_row else "",
            "trainer_place_pct_v2": trainer_row.get("trainer_place_pct_v1", "") if trainer_row else "",

            "jockey_factor_band_v2": jockey_row.get("jockey_factor_band_v1", "UNKNOWN") if jockey_row else "UNKNOWN",
            "jockey_factor_score_v2": jockey_score,
            "jockey_factor_starts_v2": jockey_row.get("jockey_starts_v1", "") if jockey_row else "",
            "jockey_win_pct_v2": jockey_row.get("jockey_win_pct_v1", "") if jockey_row else "",
            "jockey_place_pct_v2": jockey_row.get("jockey_place_pct_v1", "") if jockey_row else "",

            "combo_factor_band_v2": combo_row.get("combo_factor_band_v1", "UNKNOWN") if combo_row else "UNKNOWN",
            "combo_factor_score_v2": combo_score,
            "combo_factor_starts_v2": combo_row.get("combo_starts_v1", "") if combo_row else "",
            "combo_win_pct_v2": combo_row.get("combo_win_pct_v1", "") if combo_row else "",
            "combo_place_pct_v2": combo_row.get("combo_place_pct_v1", "") if combo_row else "",

            "trainer_jockey_blend_score_v2": blend,
            "trainer_jockey_blend_band_v2": blend_band,
            "tj_edge_label_v2": "TJ Edge: " + blend_band,
        })

        if trainer_row and jockey_row and combo_row:
            verdict = "COMPLETE"
        elif trainer_row and jockey_row:
            verdict = "TRAINER_JOCKEY_ONLY"
        elif trainer_row or jockey_row:
            verdict = "PARTIAL"
        else:
            verdict = "UNMATCHED"

        base["tj_factor_verdict_v2"] = verdict
        rows.append(base)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    unmatched = out[out["tj_factor_verdict_v2"] != "COMPLETE"].copy()
    unmatched.to_csv(OUT_UNMATCHED, index=False)

    summary = pd.DataFrame([
        ["source_file_used", LIVE.name],
        ["live_rows", len(out)],
        ["trainer_matched", int((out["trainer_factor_matched_v2"] == "YES").sum())],
        ["trainer_match_pct", round((out["trainer_factor_matched_v2"] == "YES").mean() * 100, 2)],
        ["jockey_matched", int((out["jockey_factor_matched_v2"] == "YES").sum())],
        ["jockey_match_pct", round((out["jockey_factor_matched_v2"] == "YES").mean() * 100, 2)],
        ["combo_matched", int((out["combo_factor_matched_v2"] == "YES").sum())],
        ["combo_match_pct", round((out["combo_factor_matched_v2"] == "YES").mean() * 100, 2)],
        ["complete_rows", int((out["tj_factor_verdict_v2"] == "COMPLETE").sum())],
        ["partial_or_unmatched_rows", int((out["tj_factor_verdict_v2"] != "COMPLETE").sum())],
        ["observation_only", "YES"],
        ["price_or_execution_changed", "NO"],
    ], columns=["metric", "value"])

    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "source_file_used": str(LIVE),
        "live_rows": int(len(out)),
        "trainer_match_pct": round((out["trainer_factor_matched_v2"] == "YES").mean() * 100, 2),
        "jockey_match_pct": round((out["jockey_factor_matched_v2"] == "YES").mean() * 100, 2),
        "combo_match_pct": round((out["combo_factor_matched_v2"] == "YES").mean() * 100, 2),
        "complete_rows": int((out["tj_factor_verdict_v2"] == "COMPLETE").sum()),
        "partial_or_unmatched_rows": int((out["tj_factor_verdict_v2"] != "COMPLETE").sum()),
        "observation_only": True,
        "price_or_execution_changed": False,
        "outputs": {
            "feed": str(OUT),
            "summary": str(OUT_SUMMARY),
            "unmatched": str(OUT_UNMATCHED),
        },
    }, indent=2), encoding="utf-8")

    print("[LIVE_TRAINER_JOCKEY_FACTOR_FEED_V2] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
