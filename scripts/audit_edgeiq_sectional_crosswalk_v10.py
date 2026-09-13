from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

AMB = DATA / "edgeiq_sectional_crosswalk_match_v7_ambiguous.csv"
TARGETS = [
    DATA / "edgeiq_sectional_payload_reconstruction_v1.csv",
    DATA / "sectionals.csv",
]

OUT_SUMMARY = DATA / "edgeiq_sectional_crosswalk_v10_summary.csv"
OUT_AMBIG = DATA / "edgeiq_sectional_crosswalk_v10_ambiguity_decoded.csv"
OUT_SCHEMA = DATA / "edgeiq_sectional_crosswalk_v10_target_schema_detail.csv"
OUT_MISSING = DATA / "edgeiq_sectional_crosswalk_v10_missing_identity_detail.csv"
OUT_SAMPLES = DATA / "edgeiq_sectional_crosswalk_v10_missing_identity_samples.csv"

MISSING = {"", "-", "nan", "none", "null", "undefined", "n/a", "nat"}


def clean(v):
    s = str(v or "").strip()
    return "" if s.lower() in MISSING else s


def nk(s):
    return re.sub(r"[^a-z0-9]+", "_", clean(s).lower()).strip("_")


def is_missing(v):
    return clean(v) == ""


def choose_col(fields, aliases):
    norm = {nk(x): x for x in fields}
    for a in aliases:
        if nk(a) in norm:
            return norm[nk(a)]
    return ""


def parse_candidate_token(token):
    token = clean(token)
    if not token:
        return "", ""
    if ":" in token:
        rn, rid = token.split(":", 1)
        return clean(rn), clean(rid)
    return token, ""


def main():
    summary = Counter()
    decoded = []

    # ------------------------------------------------------------------
    # 1. Decode V7 ambiguity serialization exactly as V7 wrote it:
    #    race_no:race_id|race_no:race_id|...
    # ------------------------------------------------------------------
    if AMB.exists():
        with AMB.open("r", newline="", encoding="utf-8-sig") as h:
            rd = csv.DictReader(h)
            for r in rd:
                summary["ambiguous_target_rows"] += 1
                tokens = [x for x in clean(r.get("candidates")).split("|") if clean(x)]
                pairs = [parse_candidate_token(x) for x in tokens]
                unique_pairs = sorted(set(pairs))
                race_nos = sorted({rn for rn, _ in unique_pairs if rn})
                race_ids = sorted({rid for _, rid in unique_pairs if rid})

                if len(unique_pairs) == 1:
                    cls = "ONE_UNIQUE_PAIR"
                elif len(race_ids) == 1 and len(race_ids) > 0:
                    cls = "SAME_RACE_ID_MULTIPLE_RACE_NO"
                elif len(race_nos) == 1 and len(race_nos) > 0:
                    cls = "SAME_RACE_NO_MULTIPLE_RACE_ID"
                elif not race_ids and len(race_nos) == 1:
                    cls = "SAME_RACE_NO_NO_RACE_ID"
                elif len(race_nos) > 1:
                    cls = "MULTIPLE_RACE_NUMBERS"
                else:
                    cls = "UNRESOLVED"

                summary[f"ambiguity_{cls.lower()}"] += 1
                summary["ambiguity_candidate_pairs"] += len(unique_pairs)

                decoded.append({
                    "source_file": r.get("source_file", ""),
                    "row_no": r.get("row_no", ""),
                    "race_date": r.get("race_date", ""),
                    "track": r.get("track", ""),
                    "horse_key": r.get("horse_key", ""),
                    "distance": r.get("distance", ""),
                    "candidate_count_reported": r.get("candidate_count", ""),
                    "candidate_pairs_parsed": len(unique_pairs),
                    "unique_race_nos": len(race_nos),
                    "unique_race_ids": len(race_ids),
                    "classification": cls,
                    "race_nos": "|".join(race_nos),
                    "race_ids": "|".join(race_ids),
                    "candidate_pairs": "|".join(f"{rn}:{rid}" for rn, rid in unique_pairs),
                })

    with OUT_AMBIG.open("w", newline="", encoding="utf-8") as h:
        fields = [
            "source_file", "row_no", "race_date", "track", "horse_key", "distance",
            "candidate_count_reported", "candidate_pairs_parsed", "unique_race_nos",
            "unique_race_ids", "classification", "race_nos", "race_ids", "candidate_pairs"
        ]
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader()
        w.writerows(decoded)

    # ------------------------------------------------------------------
    # 2. Full target schema / fill-rate audit.
    #    This is specifically to locate identity-bearing lineage columns
    #    that can explain the missing dates/tracks without heuristics.
    # ------------------------------------------------------------------
    schema_rows = []
    missing_rows = []
    samples = []

    identity_name_re = re.compile(
        r"(date|track|venue|meeting|race|horse|runner|event|source|file|id|key|distance|dist|url|path)",
        re.I,
    )

    for path in TARGETS:
        if not path.exists():
            continue

        with path.open("r", newline="", encoding="utf-8-sig") as h:
            rd = csv.DictReader(h)
            fields = list(rd.fieldnames or [])
            rows = list(rd)

        date_col = choose_col(fields, ["race_date", "date", "meeting_date", "run_date"])
        track_col = choose_col(fields, ["track", "track_name", "venue", "meeting"])
        horse_col = choose_col(fields, ["horse", "horse_name", "runner", "runner_name"])
        race_no_col = choose_col(fields, ["race_no", "race_number", "raceno", "race"])
        distance_col = choose_col(fields, ["distance", "race_distance", "distance_m", "dist"])

        unresolved = []
        for i, r in enumerate(rows, start=2):
            if not race_no_col or is_missing(r.get(race_no_col)):
                unresolved.append((i, r))

        for col in fields:
            nonmissing_all = sum(1 for r in rows if not is_missing(r.get(col)))
            nonmissing_unresolved = sum(1 for _, r in unresolved if not is_missing(r.get(col)))
            schema_rows.append({
                "source_file": path.name,
                "column": col,
                "identity_like_name": "YES" if identity_name_re.search(col) else "NO",
                "total_rows": len(rows),
                "nonmissing_all": nonmissing_all,
                "pct_nonmissing_all": round(nonmissing_all / len(rows) * 100, 4) if rows else 0,
                "unresolved_rows": len(unresolved),
                "nonmissing_unresolved": nonmissing_unresolved,
                "pct_nonmissing_unresolved": round(nonmissing_unresolved / len(unresolved) * 100, 4) if unresolved else 0,
            })

        miss_date = sum(1 for _, r in unresolved if not date_col or is_missing(r.get(date_col)))
        miss_track = sum(1 for _, r in unresolved if not track_col or is_missing(r.get(track_col)))
        miss_horse = sum(1 for _, r in unresolved if not horse_col or is_missing(r.get(horse_col)))
        miss_distance = sum(1 for _, r in unresolved if not distance_col or is_missing(r.get(distance_col)))

        candidate_cols = []
        for col in fields:
            n = nk(col)
            if identity_name_re.search(col):
                filled = sum(1 for _, r in unresolved if not is_missing(r.get(col)))
                if filled:
                    candidate_cols.append((col, filled))
        candidate_cols.sort(key=lambda x: (-x[1], x[0].lower()))

        missing_rows.append({
            "source_file": path.name,
            "total_rows": len(rows),
            "unresolved_rows": len(unresolved),
            "date_col": date_col,
            "track_col": track_col,
            "horse_col": horse_col,
            "race_no_col": race_no_col,
            "distance_col": distance_col,
            "missing_date": miss_date,
            "missing_track": miss_track,
            "missing_horse": miss_horse,
            "missing_distance": miss_distance,
            "identity_like_populated_columns": "|".join(f"{c}:{n}" for c, n in candidate_cols),
        })

        # Up to 25 deterministic samples from each missingness class.
        class_counts = Counter()
        for rowno, r in unresolved:
            md = (not date_col) or is_missing(r.get(date_col))
            mt = (not track_col) or is_missing(r.get(track_col))
            mh = (not horse_col) or is_missing(r.get(horse_col))

            if md and mt:
                cls = "MISSING_DATE_TRACK"
            elif md:
                cls = "MISSING_DATE_ONLY"
            elif mt:
                cls = "MISSING_TRACK_ONLY"
            elif mh:
                cls = "MISSING_HORSE_ONLY"
            else:
                cls = "HAS_DATE_TRACK_HORSE"

            if class_counts[cls] >= 25:
                continue
            class_counts[cls] += 1

            sample = {
                "source_file": path.name,
                "row_no": rowno,
                "missingness_class": cls,
            }
            for col, _ in candidate_cols[:20]:
                sample[col] = r.get(col, "")
            samples.append(sample)

        summary[f"{path.name}_rows"] = len(rows)
        summary[f"{path.name}_unresolved"] = len(unresolved)
        summary[f"{path.name}_missing_date"] = miss_date
        summary[f"{path.name}_missing_track"] = miss_track
        summary[f"{path.name}_missing_horse"] = miss_horse
        summary[f"{path.name}_missing_distance"] = miss_distance

    with OUT_SCHEMA.open("w", newline="", encoding="utf-8") as h:
        fields = [
            "source_file", "column", "identity_like_name", "total_rows", "nonmissing_all",
            "pct_nonmissing_all", "unresolved_rows", "nonmissing_unresolved", "pct_nonmissing_unresolved"
        ]
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader()
        w.writerows(schema_rows)

    with OUT_MISSING.open("w", newline="", encoding="utf-8") as h:
        fields = [
            "source_file", "total_rows", "unresolved_rows", "date_col", "track_col",
            "horse_col", "race_no_col", "distance_col", "missing_date", "missing_track",
            "missing_horse", "missing_distance", "identity_like_populated_columns"
        ]
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader()
        w.writerows(missing_rows)

    # Samples can have differing dynamic columns; union safely.
    sample_fields = ["source_file", "row_no", "missingness_class"]
    extra = []
    seen = set(sample_fields)
    for r in samples:
        for k in r:
            if k not in seen:
                seen.add(k)
                extra.append(k)
    with OUT_SAMPLES.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=sample_fields + extra, extrasaction="ignore")
        w.writeheader()
        w.writerows(samples)

    with OUT_SUMMARY.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["metric", "value"])
        for k, v in summary.items():
            w.writerow([k, v])

    print("=" * 92)
    print("EDGEIQ SECTIONAL CROSSWALK V10 — AMBIGUITY DECODE + LINEAGE AUDIT")
    print("=" * 92)
    for k, v in summary.items():
        print(f"{k}: {v}")

    print("\nAMBIGUITY CLASSIFICATIONS")
    print("-" * 92)
    cls_counts = Counter(r["classification"] for r in decoded)
    for k, v in cls_counts.most_common():
        print(f"{k}: {v}")

    print("\nTARGET IDENTITY-LIKE POPULATED COLUMNS")
    print("-" * 92)
    for r in missing_rows:
        print(f"SOURCE={r['source_file']}")
        print(f"  unresolved_rows={r['unresolved_rows']}")
        print(f"  missing_date={r['missing_date']}")
        print(f"  missing_track={r['missing_track']}")
        print(f"  missing_horse={r['missing_horse']}")
        print(f"  missing_distance={r['missing_distance']}")
        print(f"  columns={r['identity_like_populated_columns']}")

    print("\nOUTPUTS")
    print(OUT_SUMMARY)
    print(OUT_AMBIG)
    print(OUT_SCHEMA)
    print(OUT_MISSING)
    print(OUT_SAMPLES)


if __name__ == "__main__":
    main()
