from __future__ import annotations

import re
from pathlib import Path
import pandas as pd

APP_ROOT = Path.cwd()
PROJECT_ROOT = APP_ROOT.parents[1]
PUBLIC_DATA = APP_ROOT / "public" / "data"

FIELDS_PATH = PUBLIC_DATA / "race_fields.csv"
OUT_FULL = PUBLIC_DATA / "full_career_form.csv"
OUT_RUNS = PUBLIC_DATA / "form_card_runs.csv"
OUT_SUMMARY = PUBLIC_DATA / "form_coverage_report.csv"
OUT_MISSING = PUBLIC_DATA / "missing_form_horses.csv"

COUNTRY_SUFFIX_RE = re.compile(r"\([A-Z]{2,4}\)")
NON_ALNUM_RE = re.compile(r"[^A-Z0-9]")


def compact(value) -> str:
    if value is None or pd.isna(value):
        return ""
    s = str(value).upper().strip()
    s = COUNTRY_SUFFIX_RE.sub("", s)
    s = NON_ALNUM_RE.sub("", s)
    return s


def read_csv_safe(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return None


def pick_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def standardise_form(df: pd.DataFrame, source_file: str) -> pd.DataFrame | None:
    horse_col = pick_col(df, ["horse", "horse_name", "runner", "runner_name"])
    key_col = pick_col(df, ["horse_key", "horsekey", "runner_key"])
    date_col = pick_col(df, ["run_date", "date", "race_date"])
    track_col = pick_col(df, ["track"])
    type_col = pick_col(df, ["run_type", "type"])
    rating_col = pick_col(df, ["run_rating", "rating", "rating_display"])
    class_col = pick_col(df, ["race_class", "class_name", "class"])
    cond_col = pick_col(df, ["track_condition", "condition"])
    finish_col = pick_col(df, ["finish_pos", "fin", "position"])
    margin_col = pick_col(df, ["margin"])
    jockey_col = pick_col(df, ["jockey"])
    sp_col = pick_col(df, ["sp_text", "starting_price", "sp"])
    field_size_col = pick_col(df, ["field_size"])
    trainer_col = pick_col(df, ["trainer"])
    barrier_col = pick_col(df, ["barrier", "bar"])
    weight_col = pick_col(df, ["weight_carried", "weight", "wgt"])
    time_col = pick_col(df, ["official_time", "time"])
    winner_col = pick_col(df, ["winner"])
    second_col = pick_col(df, ["second"])
    pos800_col = pick_col(df, ["pos_800", "pos800"])
    pos400_col = pick_col(df, ["pos_400", "pos400"])
    inrun_col = pick_col(df, ["in_run_positions", "inrun"])
    source_url_col = pick_col(df, ["source_url", "url"])

    if horse_col is None or date_col is None or track_col is None:
        return None

    out = pd.DataFrame()
    out["horse"] = df[horse_col].astype(str).str.strip()
    out["horse_key"] = df[key_col].map(compact) if key_col else out["horse"].map(compact)
    out.loc[out["horse_key"].eq(""), "horse_key"] = out.loc[out["horse_key"].eq(""), "horse"].map(compact)
    out["run_date"] = df[date_col].astype(str).str.strip()
    out["track"] = df[track_col].astype(str).str.strip()
    out["distance"] = df[pick_col(df, ["distance", "dist"])].astype(str).str.strip() if pick_col(df, ["distance", "dist"]) else ""
    out["race_class"] = df[class_col].astype(str).str.strip() if class_col else ""
    out["track_condition"] = df[cond_col].astype(str).str.strip() if cond_col else ""
    out["finish_pos"] = df[finish_col].astype(str).str.strip() if finish_col else ""
    out["field_size"] = df[field_size_col].astype(str).str.strip() if field_size_col else ""
    out["margin"] = df[margin_col].astype(str).str.strip() if margin_col else ""
    out["jockey"] = df[jockey_col].astype(str).str.strip() if jockey_col else ""
    out["trainer"] = df[trainer_col].astype(str).str.strip() if trainer_col else ""
    out["barrier"] = df[barrier_col].astype(str).str.strip() if barrier_col else ""
    out["weight_carried"] = df[weight_col].astype(str).str.strip() if weight_col else ""
    out["sp_text"] = df[sp_col].astype(str).str.strip() if sp_col else ""
    out["starting_price"] = df[sp_col].astype(str).str.strip() if sp_col else ""
    out["official_time"] = df[time_col].astype(str).str.strip() if time_col else ""
    out["winner"] = df[winner_col].astype(str).str.strip() if winner_col else ""
    out["second"] = df[second_col].astype(str).str.strip() if second_col else ""
    out["pos_800"] = df[pos800_col].astype(str).str.strip() if pos800_col else ""
    out["pos_400"] = df[pos400_col].astype(str).str.strip() if pos400_col else ""
    out["in_run_positions"] = df[inrun_col].astype(str).str.strip() if inrun_col else ""
    out["run_type"] = df[type_col].astype(str).str.upper().str.strip() if type_col else "RACE"
    out["run_type"] = out["run_type"].replace({"": "RACE", "NAN": "RACE", "TRUE": "RACE", "FALSE": "RACE"})
    out["run_rating"] = pd.to_numeric(df[rating_col], errors="coerce") if rating_col else pd.NA
    out.loc[out["run_type"].ne("RACE"), "run_rating"] = pd.NA
    out["rating_display"] = out.apply(
        lambda r: f"{r['run_rating']:.1f}" if pd.notna(r["run_rating"]) and r["run_type"] == "RACE" else ("—" if r["run_type"] != "RACE" else ""),
        axis=1,
    )
    out["source_url"] = df[source_url_col].astype(str).str.strip() if source_url_col else ""
    out["_source_file"] = source_file

    out = out[
        out["horse_key"].ne("")
        & out["run_date"].ne("")
        & out["track"].ne("")
        & out["horse"].ne("")
        & out["horse"].str.lower().ne("nan")
    ].copy()

    out["_dedupe"] = (
        out["horse_key"].astype(str)
        + "|"
        + out["run_date"].astype(str)
        + "|"
        + out["track"].astype(str)
        + "|"
        + out["distance"].astype(str)
        + "|"
        + out["finish_pos"].astype(str)
        + "|"
        + out["run_type"].astype(str)
    )

    return out


def main() -> None:
    if not FIELDS_PATH.exists():
        raise SystemExit("MISSING public/data/race_fields.csv")

    fields = pd.read_csv(FIELDS_PATH, low_memory=False)
    fields["horse_key_norm"] = fields["horse_key"].map(compact)
    fields.loc[fields["horse_key_norm"].eq(""), "horse_key_norm"] = fields["horse"].map(compact)

    today_keys = set(fields["horse_key_norm"].dropna().astype(str))
    today_keys.discard("")
    today_keys.discard("0")

    csv_paths = sorted(PROJECT_ROOT.rglob("*.csv"))

    frames: list[pd.DataFrame] = []
    used_files: list[str] = []

    for path in csv_paths:
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if "node_modules" in rel or "/dist/" in rel:
            continue

        df = read_csv_safe(path)
        if df is None or df.empty:
            continue

        std = standardise_form(df, rel)
        if std is None or std.empty:
            continue

        std = std[std["horse_key"].isin(today_keys)].copy()
        if std.empty:
            continue

        frames.append(std)
        used_files.append(rel)

    if frames:
        combined = pd.concat(frames, ignore_index=True)
    else:
        combined = pd.DataFrame(columns=[
            "horse", "horse_key", "run_date", "track", "distance", "race_class", "track_condition",
            "finish_pos", "field_size", "margin", "jockey", "trainer", "barrier", "weight_carried",
            "sp_text", "starting_price", "official_time", "winner", "second", "pos_800", "pos_400",
            "in_run_positions", "run_type", "run_rating", "rating_display", "source_url", "_source_file", "_dedupe"
        ])

    combined = combined.drop_duplicates("_dedupe", keep="first").copy()
    combined["run_date_sort"] = pd.to_datetime(combined["run_date"], errors="coerce")
    combined = combined.sort_values(["horse_key", "run_date_sort"], ascending=[True, False]).drop(columns=["run_date_sort"])

    public_cols = [
        "horse", "horse_key", "run_date", "track", "distance", "race_class", "track_condition",
        "finish_pos", "field_size", "margin", "jockey", "trainer", "barrier", "weight_carried",
        "sp_text", "starting_price", "official_time", "winner", "second", "pos_800", "pos_400",
        "in_run_positions", "run_type", "run_rating", "rating_display", "source_url"
    ]

    OUT_FULL.parent.mkdir(parents=True, exist_ok=True)
    combined[public_cols].to_csv(OUT_FULL, index=False)
    combined[public_cols].to_csv(OUT_RUNS, index=False)

    coverage = (
        fields[["race_date", "track", "race_no", "horse_no", "horse", "horse_key_norm"]]
        .drop_duplicates()
        .copy()
    )

    counts = combined.groupby("horse_key").size().rename("form_rows").reset_index()
    race_counts = combined[combined["run_type"].eq("RACE")].groupby("horse_key").size().rename("race_rows").reset_index()
    coverage = coverage.merge(counts, left_on="horse_key_norm", right_on="horse_key", how="left")
    coverage = coverage.merge(race_counts, left_on="horse_key_norm", right_on="horse_key", how="left", suffixes=("", "_race"))
    coverage["form_rows"] = coverage["form_rows"].fillna(0).astype(int)
    coverage["race_rows"] = coverage["race_rows"].fillna(0).astype(int)
    coverage["has_form"] = coverage["form_rows"] > 0
    coverage["has_official_race"] = coverage["race_rows"] > 0
    coverage = coverage.drop(columns=[c for c in ["horse_key", "horse_key_race"] if c in coverage.columns])

    missing = coverage[~coverage["has_form"]].copy()

    coverage.to_csv(OUT_SUMMARY, index=False)
    missing.to_csv(OUT_MISSING, index=False)

    print("FORM COVERAGE REBUILD COMPLETE")
    print("Project root:", PROJECT_ROOT)
    print("CSV sources used:", len(used_files))
    for f in used_files[:40]:
        print(" -", f)
    if len(used_files) > 40:
        print(" ...", len(used_files) - 40, "more")
    print()
    print("Today runners:", len(coverage))
    print("With any form:", int(coverage["has_form"].sum()))
    print("Missing form:", len(missing))
    print("With official race form:", int(coverage["has_official_race"].sum()))
    print()
    print("Wrote:", OUT_FULL)
    print("Wrote:", OUT_RUNS)
    print("Wrote:", OUT_SUMMARY)
    print("Wrote:", OUT_MISSING)

    if len(missing):
        print()
        print("FIRST 30 STILL MISSING:")
        print(missing[["track", "race_no", "horse_no", "horse", "horse_key_norm"]].head(30).to_string(index=False))


if __name__ == "__main__":
    main()
