from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
TRAINER = DATA / "edgeiq_trainer_factor_v1.csv"
JOCKEY = DATA / "edgeiq_jockey_factor_v1.csv"

OUT_TRAINER = DATA / "edgeiq_live_trainer_match_audit_v1.csv"
OUT_JOCKEY = DATA / "edgeiq_live_jockey_match_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_trainer_jockey_match_summary_v1.csv"
OUT_JSON = DATA / "edgeiq_live_trainer_jockey_match_audit_v1.json"


def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def clean(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))


def clean_live_name(x):
    s = norm(x)
    s = s.replace("(LATE ALT)", "")
    s = re.sub(r"\(A[0-9.]*\/?[0-9A-Z.]*KG?\)", "", s)
    s = re.sub(r"\(A[0-9.]*\)", "", s)
    s = re.sub(r"\([^)]+\)", "", s)
    s = s.replace("MS ", "").replace("MR ", "").replace("MRS ", "").replace("MISS ", "")
    return " ".join(s.split())


def initial_surname_key(name):
    s = clean_live_name(name)
    parts = [p for p in s.split(" ") if p]
    if len(parts) < 2:
        return clean(s)

    first = parts[0]
    last = parts[-1]

    if len(parts) >= 3:
        middle = parts[1]
        return clean(first[0] + middle[0] + last)

    return clean(first[0] + last)


def first_surname_key(name):
    s = clean_live_name(name)
    parts = [p for p in s.split(" ") if p]
    if len(parts) < 2:
        return clean(s)
    return clean(parts[0] + parts[-1])


def surname_key(name):
    s = clean_live_name(name)
    parts = [p for p in s.split(" ") if p]
    if not parts:
        return ""
    return clean(parts[-1])


def build_factor_key_sets(df, key_col, name_col):
    keys = set(clean(x) for x in df[key_col].dropna().astype(str))
    name_to_key = {}

    for _, r in df.iterrows():
        k = clean(r.get(key_col, ""))
        n = clean_live_name(r.get(name_col, ""))

        if k:
            name_to_key.setdefault(k, k)

        # Also store exact compact name form from historical text.
        if n:
            name_to_key.setdefault(clean(n), k)

    surname_index = {}
    for _, r in df.iterrows():
        k = clean(r.get(key_col, ""))
        n = clean_live_name(r.get(name_col, ""))
        sn = surname_key(n)
        if sn and k:
            surname_index.setdefault(sn, set()).add(k)

    return keys, name_to_key, surname_index


def audit_entity(live, factor, live_col, key_col, name_col, entity_type):
    factor_keys, factor_name_lookup, surname_index = build_factor_key_sets(factor, key_col, name_col)

    rows = []
    grouped = (
        live.groupby(live_col, dropna=False)
        .agg(
            live_rows=("horse", "size"),
            tracks=("track", lambda s: "|".join(sorted(set(map(str, s))))),
            sample_horses=("horse", lambda s: " | ".join(list(map(str, s.head(5))))),
        )
        .reset_index()
        .sort_values("live_rows", ascending=False)
    )

    for _, r in grouped.iterrows():
        live_name = r[live_col]
        cleaned_name = clean_live_name(live_name)

        exact_key = clean(cleaned_name)
        init_key = initial_surname_key(live_name)
        first_key = first_surname_key(live_name)
        sn_key = surname_key(live_name)

        exact_match = exact_key in factor_keys or exact_key in factor_name_lookup
        initial_match = init_key in factor_keys or init_key in factor_name_lookup
        first_match = first_key in factor_keys or first_key in factor_name_lookup

        surname_candidates = sorted(list(surname_index.get(sn_key, set())))
        surname_unique_match = len(surname_candidates) == 1

        matched_key = ""
        match_method = "UNMATCHED"

        if exact_match:
            matched_key = factor_name_lookup.get(exact_key, exact_key)
            match_method = "EXACT"
        elif initial_match:
            matched_key = factor_name_lookup.get(init_key, init_key)
            match_method = "INITIAL_SURNAME"
        elif first_match:
            matched_key = factor_name_lookup.get(first_key, first_key)
            match_method = "FIRST_SURNAME"
        elif surname_unique_match:
            matched_key = surname_candidates[0]
            match_method = "UNIQUE_SURNAME"

        rows.append({
            "entity_type": entity_type,
            "live_name": live_name,
            "cleaned_live_name": cleaned_name,
            "live_rows": r["live_rows"],
            "tracks": r["tracks"],
            "sample_horses": r["sample_horses"],
            "exact_compact_key": exact_key,
            "initial_surname_key": init_key,
            "first_surname_key": first_key,
            "surname_key": sn_key,
            "exact_match": "YES" if exact_match else "NO",
            "initial_surname_match": "YES" if initial_match else "NO",
            "first_surname_match": "YES" if first_match else "NO",
            "surname_candidate_count": len(surname_candidates),
            "surname_candidates": "|".join(surname_candidates[:20]),
            "suggested_factor_key": matched_key,
            "suggested_match_method": match_method,
            "would_match": "YES" if matched_key else "NO",
        })

    return pd.DataFrame(rows)


def main():
    for f in [LIVE, TRAINER, JOCKEY]:
        if not f.exists():
            raise FileNotFoundError(f"Missing required file: {f}")

    live = pd.read_csv(LIVE, low_memory=False)
    trainer = pd.read_csv(TRAINER, low_memory=False)
    jockey = pd.read_csv(JOCKEY, low_memory=False)

    for c in ["track", "horse", "trainer", "jockey"]:
        if c not in live.columns:
            raise ValueError(f"Live board missing column: {c}")

    trainer_audit = audit_entity(
        live=live,
        factor=trainer,
        live_col="trainer",
        key_col="trainer_key",
        name_col="trainer",
        entity_type="TRAINER",
    )

    jockey_audit = audit_entity(
        live=live,
        factor=jockey,
        live_col="jockey",
        key_col="jockey_key",
        name_col="jockey",
        entity_type="JOCKEY",
    )

    trainer_audit.to_csv(OUT_TRAINER, index=False)
    jockey_audit.to_csv(OUT_JOCKEY, index=False)

    trainer_live_rows = int(trainer_audit["live_rows"].sum())
    jockey_live_rows = int(jockey_audit["live_rows"].sum())

    trainer_would_match_rows = int(trainer_audit[trainer_audit["would_match"] == "YES"]["live_rows"].sum())
    jockey_would_match_rows = int(jockey_audit[jockey_audit["would_match"] == "YES"]["live_rows"].sum())

    summary = pd.DataFrame([
        ["live_rows", len(live)],
        ["unique_live_trainers", len(trainer_audit)],
        ["trainer_would_match_rows", trainer_would_match_rows],
        ["trainer_would_match_pct", round(trainer_would_match_rows / trainer_live_rows * 100, 2) if trainer_live_rows else 0],
        ["trainer_unmatched_names", int((trainer_audit["would_match"] != "YES").sum())],
        ["unique_live_jockeys", len(jockey_audit)],
        ["jockey_would_match_rows", jockey_would_match_rows],
        ["jockey_would_match_pct", round(jockey_would_match_rows / jockey_live_rows * 100, 2) if jockey_live_rows else 0],
        ["jockey_unmatched_names", int((jockey_audit["would_match"] != "YES").sum())],
        ["audit_only", "YES"],
        ["price_or_execution_changed", "NO"],
    ], columns=["metric", "value"])

    summary.to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "live_rows": int(len(live)),
        "trainer_would_match_pct": round(trainer_would_match_rows / trainer_live_rows * 100, 2) if trainer_live_rows else 0,
        "jockey_would_match_pct": round(jockey_would_match_rows / jockey_live_rows * 100, 2) if jockey_live_rows else 0,
        "outputs": {
            "trainer_audit": str(OUT_TRAINER),
            "jockey_audit": str(OUT_JOCKEY),
            "summary": str(OUT_SUMMARY),
        },
        "important_note": "Audit only. No fair price, no execution, no UI change.",
    }, indent=2), encoding="utf-8")

    print("[LIVE_TRAINER_JOCKEY_MATCH_AUDIT_V1] COMPLETE")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
