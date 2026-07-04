from pathlib import Path
import json
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"

OUT_ALIAS = DATA / "edgeiq_trainer_jockey_alias_map_v1.csv"
OUT_CANON = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_trainer_jockey_canonicalisation_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_trainer_jockey_canonicalisation_v1.json"

TRAINER_MANUAL = {
    "ANTHONY & SAM FREEDMAN": "A. & S.FREEDMAN",
    "A. & S.FREEDMAN": "A. & S.FREEDMAN",
    "MICK PRICE & MICHAEL KENT (JNR)": "M.PRICE & M.KENT (JNR)",
    "M.PRICE & M.KENT (JNR)": "M.PRICE & M.KENT (JNR)",
    "TONY & CALVIN MCEVOY": "T. & C.MCEVOY",
    "T. & C.MCEVOY": "T. & C.MCEVOY",
    "BEN, WILL & JD HAYES": "B. & W. & JD.HAYES",
    "B. & JD.HAYES": "B. & W. & JD.HAYES",
    "B. & W. & JD.HAYES": "B. & W. & JD.HAYES",
    "PETER G MOODY & KATHERINE COLEMAN": "P.G.MOODY & K.COLEMAN",
    "P.G.MOODY & K.COLEMAN": "P.G.MOODY & K.COLEMAN",
    "GAI WATERHOUSE & ADRIAN BOTT": "G.WATERHOUSE & A.BOTT",
    "G.WATERHOUSE & A.BOTT": "G.WATERHOUSE & A.BOTT",
    "PATRICK & MICHELLE PAYNE": "P. & M.PAYNE",
    "P. & M.PAYNE": "P. & M.PAYNE",
}

JOCKEY_MANUAL = {
    "B.A.SHINN": "B.SHINN",
    "B.SHINN": "B.SHINN",
    "J.B.MCDONALD": "J.MCDONALD",
    "J.MCDONALD": "J.MCDONALD",
    "D.M.LANE": "D.LANE",
    "D.LANE": "D.LANE",
    "E.P.BROWN": "E.BROWN",
    "E.BROWN": "E.BROWN",
    "C.G.GAUDRAY (A2)": "C.GAUDRAY",
    "C.GAUDRAY (A1.5)": "C.GAUDRAY",
    "C.GAUDRAY": "C.GAUDRAY",
    "T.STOCKDALE (A0)": "T.STOCKDALE",
    "T.STOCKDALE": "T.STOCKDALE",
    "S.CLARKE (A1.5)": "S.CLARKE",
    "S.CLARKE": "S.CLARKE",
}

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def clean_key(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))

def remove_claim(name):
    return re.sub(r"\s*\(A[0-9.]*\)\s*", "", norm(name)).strip()

def canonical_name(name, manual):
    n = norm(name)
    if n in manual:
        return manual[n]
    n2 = remove_claim(n)
    if n2 in manual:
        return manual[n2]
    return n2

def main():
    if not HIST.exists():
        raise FileNotFoundError(f"Missing input: {HIST}")

    df = pd.read_csv(HIST, low_memory=False)

    df["trainer_canonical"] = df["trainer"].apply(lambda x: canonical_name(x, TRAINER_MANUAL))
    df["jockey_canonical"] = df["jockey"].apply(lambda x: canonical_name(x, JOCKEY_MANUAL))

    df["trainer_canonical_key"] = df["trainer_canonical"].map(clean_key)
    df["jockey_canonical_key"] = df["jockey_canonical"].map(clean_key)
    df["trainer_jockey_canonical_key"] = df["trainer_canonical_key"] + "|" + df["jockey_canonical_key"]
    df["trainer_jockey_canonical"] = df["trainer_canonical"] + " + " + df["jockey_canonical"]

    trainer_alias = (
        df[["trainer", "trainer_key", "trainer_canonical", "trainer_canonical_key"]]
        .drop_duplicates()
        .rename(columns={
            "trainer": "original_name",
            "trainer_key": "original_key",
            "trainer_canonical": "canonical_name",
            "trainer_canonical_key": "canonical_key",
        })
    )
    trainer_alias["entity_type"] = "TRAINER"

    jockey_alias = (
        df[["jockey", "jockey_key", "jockey_canonical", "jockey_canonical_key"]]
        .drop_duplicates()
        .rename(columns={
            "jockey": "original_name",
            "jockey_key": "original_key",
            "jockey_canonical": "canonical_name",
            "jockey_canonical_key": "canonical_key",
        })
    )
    jockey_alias["entity_type"] = "JOCKEY"

    alias = pd.concat([trainer_alias, jockey_alias], ignore_index=True)

    summary = pd.DataFrame([
        ["raw_rows", len(df)],
        ["original_trainers", df["trainer_key"].nunique()],
        ["canonical_trainers", df["trainer_canonical_key"].nunique()],
        ["trainer_reduction", df["trainer_key"].nunique() - df["trainer_canonical_key"].nunique()],
        ["original_jockeys", df["jockey_key"].nunique()],
        ["canonical_jockeys", df["jockey_canonical_key"].nunique()],
        ["jockey_reduction", df["jockey_key"].nunique() - df["jockey_canonical_key"].nunique()],
        ["original_combos", df["trainer_jockey_key_v1"].nunique()],
        ["canonical_combos", df["trainer_jockey_canonical_key"].nunique()],
        ["combo_reduction", df["trainer_jockey_key_v1"].nunique() - df["trainer_jockey_canonical_key"].nunique()],
    ], columns=["metric", "value"])

    df.to_csv(OUT_CANON, index=False)
    alias.to_csv(OUT_ALIAS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "canonical_history": str(OUT_CANON),
        "alias_map": str(OUT_ALIAS),
        "summary": str(OUT_SUMMARY),
    }, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_CANONICALISATION_V1] COMPLETE")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()
