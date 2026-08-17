from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from edgeiq_class_taxonomy_v1 import (
    canonical_class_family,
    canonicalization_confidence,
    canonicalize_race_class,
    class_par_lookup,
    class_par_match_status,
    norm,
    normalized_class_text,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "race_fields.csv"
CLASS_PARS = DATA / "edgeiq_class_pars_v5_2.csv"
OUT = DATA / "edgeiq_current_race_class_correction_v5_1.csv"
AUDIT = DATA / "edgeiq_current_race_class_correction_v5_1_audit.csv"


def clean_race_no(value: object) -> str:
    return re.sub(r"\.0$", "", str(value).strip())


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def build_par_lookup() -> set[str]:
    if not CLASS_PARS.exists():
        return set()
    class_pars = pd.read_csv(CLASS_PARS, dtype=str, keep_default_na=False, low_memory=False)
    if "race_class_clean_v5_2" not in class_pars.columns:
        return set()
    return class_par_lookup(class_pars["race_class_clean_v5_2"].tolist())


def audit_row(
    section: str,
    metric: str,
    value: object = "",
    race_date: str = "",
    track: str = "",
    race_no: str = "",
    horse: str = "",
    raw_race_class: str = "",
    corrected_race_class: str = "",
    canonical_class_for_par: str = "",
    par_match_status: str = "",
    notes: str = "",
    built_at: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "raw_race_class": raw_race_class,
        "corrected_race_class_v5_1": corrected_race_class,
        "canonical_class_for_par_v5_1": canonical_class_for_par,
        "par_match_status_v5_1": par_match_status,
        "notes": notes,
        "built_at": built_at,
    }


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print("=" * 90)
    print("EDGEIQ CURRENT RACE CLASS CORRECTION V5.1 - LIVE FEED REBUILD")
    print("=" * 90)

    if not LIVE_FEED.exists():
        raise FileNotFoundError(f"Missing input: {LIVE_FEED}")

    live = pd.read_csv(LIVE_FEED, dtype=str, keep_default_na=False, low_memory=False)

    pipeline_date = os.environ.get("EDGEIQ_PIPELINE_DATE", "").strip()
    if not pipeline_date:
        raise ValueError(
            "EDGEIQ_PIPELINE_DATE is required for current race class correction"
        )

    live["race_date"] = live["race_date"].astype(str).str.strip()
    live = live[live["race_date"].eq(pipeline_date)].copy()

    if live.empty:
        raise ValueError(
            f"CURRENT_CLASS_CORRECTION_UNIVERSE_EMPTY: "
            f"EDGEIQ_PIPELINE_DATE={pipeline_date}; source={LIVE_FEED}"
        )

    contamination = live.loc[
        ~live["race_date"].eq(pipeline_date),
        "race_date"
    ].drop_duplicates().tolist()

    if contamination:
        raise ValueError(
            f"CURRENT_CLASS_CORRECTION_DATE_CONTAMINATION: "
            f"expected={pipeline_date}; found={contamination}"
        )

    required = {"race_date", "track", "race_no", "horse", "race_class"}
    missing = sorted(required.difference(live.columns))
    if missing:
        raise ValueError(f"Missing live feed columns: {missing}")

    available_par_classes = build_par_lookup()

    live["race_no"] = live["race_no"].map(clean_race_no)
    live["raw_race_class_v5_1"] = live["race_class"].map(lambda value: "" if pd.isna(value) else str(value).strip())
    live["original_race_class_clean_v5_1"] = live["race_class"].map(normalized_class_text)

    taxonomy = live["race_class"].map(canonicalize_race_class)
    live["corrected_race_class_v5_1"] = taxonomy.map(lambda item: item[0])
    live["canonical_class_for_par_v5_1"] = live["corrected_race_class_v5_1"]
    live["class_taxonomy_reason_v5_1"] = taxonomy.map(lambda item: item[1])
    live["corrected_class_family_v5_1"] = live["corrected_race_class_v5_1"].map(canonical_class_family)
    live["class_correction_applied_v5_1"] = (
        live["original_race_class_clean_v5_1"] != live["corrected_race_class_v5_1"]
    ).map(bool_text)
    live["class_correction_confidence_v5_1"] = live.apply(
        lambda row: canonicalization_confidence(
            row.get("race_class", ""),
            row.get("corrected_race_class_v5_1", ""),
            row.get("class_taxonomy_reason_v5_1", ""),
        ),
        axis=1,
    )
    live["class_correction_source_v5_1"] = "LIVE_FEED_REBUILD_CANONICAL_TAXONOMY"
    live["class_correction_reason_v5_1"] = live["class_taxonomy_reason_v5_1"]
    live["par_match_status_v5_1"] = live["canonical_class_for_par_v5_1"].map(
        lambda value: class_par_match_status(value, available_par_classes)
    )
    live["target_status_after_estimate_v5_1"] = live["par_match_status_v5_1"].map(
        lambda status: "TARGET_POSSIBLE_AFTER_CLASS_CORRECTION"
        if status in {"MATCHED_CLASS_PAR", "FALLBACK_CLASS_PAR_AVAILABLE_FROM_BM70"}
        else "NO_TARGET_ESTIMATE"
    )
    live["no_target_before_v5_1"] = live["original_race_class_clean_v5_1"].isin(["", "UNKNOWN"]).map(bool_text)
    live["no_target_after_estimate_v5_1"] = live["target_status_after_estimate_v5_1"].eq("NO_TARGET_ESTIMATE").map(bool_text)
    live["built_at_class_correction_v5_1"] = built_at

    keep = [
        "race_date",
        "track",
        "race_no",
        "race_time",
        "distance",
        "horse",
        "horse_key",
        "race_class",
        "raw_race_class_v5_1",
        "original_race_class_clean_v5_1",
        "corrected_race_class_v5_1",
        "canonical_class_for_par_v5_1",
        "par_match_status_v5_1",
        "class_taxonomy_reason_v5_1",
        "corrected_class_family_v5_1",
        "class_correction_applied_v5_1",
        "class_correction_confidence_v5_1",
        "class_correction_source_v5_1",
        "class_correction_reason_v5_1",
        "target_status_after_estimate_v5_1",
        "no_target_before_v5_1",
        "no_target_after_estimate_v5_1",
        "built_at_class_correction_v5_1",
    ]

    for column in keep:
        if column not in live.columns:
            live[column] = ""

    out = live[keep].copy()
    out.to_csv(OUT, index=False, encoding="utf-8")

    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "live_rows_loaded", value=len(live), built_at=built_at),
        audit_row("overall", "rows_written", value=len(out), built_at=built_at),
        audit_row(
            "overall",
            "current_races",
            value=out[["race_date", "track", "race_no"]].drop_duplicates().shape[0],
            built_at=built_at,
        ),
        audit_row(
            "overall",
            "available_class_par_classes",
            value=len(available_par_classes),
            notes="|".join(sorted(available_par_classes)) if available_par_classes else "class_pars_unavailable",
            built_at=built_at,
        ),
    ]

    for corrected_class, count in out["corrected_race_class_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("class_counts", corrected_class, value=int(count), built_at=built_at))

    for par_status, count in out["par_match_status_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("par_match_counts", par_status, value=int(count), built_at=built_at))

    for row in out.itertuples(index=False):
        audit_rows.append(
            audit_row(
                section="runner_taxonomy_audit",
                metric="runner_class_taxonomy",
                race_date=str(row.race_date),
                track=str(row.track),
                race_no=str(row.race_no),
                horse=str(row.horse),
                raw_race_class=str(row.raw_race_class_v5_1),
                corrected_race_class=str(row.corrected_race_class_v5_1),
                canonical_class_for_par=str(row.canonical_class_for_par_v5_1),
                par_match_status=str(row.par_match_status_v5_1),
                notes=f"raw_clean={row.original_race_class_clean_v5_1}; reason={row.class_taxonomy_reason_v5_1}",
                built_at=built_at,
            )
        )

    pd.DataFrame(audit_rows).to_csv(AUDIT, index=False, encoding="utf-8")

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print(
        out[
            [
                "race_date",
                "track",
                "race_no",
                "horse",
                "race_class",
                "corrected_race_class_v5_1",
                "canonical_class_for_par_v5_1",
                "par_match_status_v5_1",
            ]
        ].head(30).to_string(index=False)
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
