from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

SOURCES = {
    "probability_v4": DATA / "edgeiq_probability_engine_v4.csv",
    "race_shape_v2": DATA / "edgeiq_race_shape_engine_v2.csv",
    "energy_profile_v1": DATA / "edgeiq_horse_energy_profile_v1.csv",
    "live_speed_map_v3": DATA / "live_speed_map_v3.csv",
    "live_runner_board_v1": DATA / "edgeiq_live_runner_board_v1.csv",
    "execution_quality_v2": DATA / "edgeiq_execution_quality_v2.csv",
    "capital_allocation_v1": DATA / "edgeiq_capital_allocation_v1.csv",
}

OUT = DATA / "edgeiq_universal_race_identity_v2.csv"
DIAG = DATA / "edgeiq_universal_race_identity_v2_diagnostics.csv"

COUNTRY_SUFFIXES = [
    "NZ","GB","IRE","FR","USA","SAF","GER","JPN","JAP",
    "CAN","AUS","ARG","CHI","BRZ","ITY"
]

TRACK_ALIASES = {
    "BET365 STAWELL": "STAWELL",
    "SPORTSBET GAWLER": "GAWLER",
    "PICKLEBET PARK WERRIBEE": "WERRIBEE",
}

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def canon(v):
    s = safe(v).upper()

    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    s = re.sub(r"\([^)]*\)", "", s)

    for suffix in COUNTRY_SUFFIXES:
        s = re.sub(rf"\b{suffix}\b$", "", s).strip()

    s = s.replace("&", "AND")

    s = re.sub(r"[^A-Z0-9]", "", s)

    return s

def norm_track(v):
    s = safe(v).upper()
    return TRACK_ALIASES.get(s, s)

def norm_race(v):
    s = safe(v)
    if s.endswith(".0"):
        s = s[:-2]
    return s

def load_source(name, path):

    if not path.exists():
        print(f"[missing] {name}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, low_memory=False)

        df.columns = [c.strip() for c in df.columns]

        if "horse" not in df.columns:
            return pd.DataFrame()

        if "track" not in df.columns:
            df["track"] = ""

        if "race_no" not in df.columns:
            df["race_no"] = ""

        if "race_date" not in df.columns:
            df["race_date"] = ""

        df["horse_key"] = df["horse"].apply(canon)
        df["track_key"] = df["track"].apply(norm_track)
        df["race_key"] = df["race_no"].apply(norm_race)

        df["universal_race_key"] = (
            df["track_key"].astype(str)
            + "_R"
            + df["race_key"].astype(str)
        )

        df["universal_runner_key"] = (
            df["universal_race_key"]
            + "_"
            + df["horse_key"]
        )

        df["source_name"] = name

        return df

    except Exception as e:
        print(f"[failed] {name}: {repr(e)}")
        return pd.DataFrame()

frames = []

print("=" * 100)
print("EDGEIQ UNIVERSAL RACE IDENTITY ENGINE V2")
print("=" * 100)

for name, path in SOURCES.items():

    df = load_source(name, path)

    if df.empty:
        continue

    print()
    print(f"{name}")
    print("rows:", len(df))

    coverage = (
        df["universal_runner_key"]
        .notna()
        .sum()
    )

    print("identity_rows:", coverage)

    keep_cols = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "track_key",
        "race_key",
        "universal_race_key",
        "universal_runner_key",
        "source_name",
    ]

    extra_cols = []

    for c in [
        "market_price",
        "live_price",
        "v3_probability",
        "tempo_adjusted_probability",
        "dynamic_fair_price",
        "projected_race_shape",
        "tempo_fit_v2",
        "energy_archetype",
        "execution_quality",
        "execution_conviction",
        "recommended_stake",
    ]:
        if c in df.columns:
            extra_cols.append(c)

    frames.append(df[keep_cols + extra_cols].copy())

master = pd.concat(frames, ignore_index=True)

coverage = (
    master.groupby("universal_runner_key")["source_name"]
    .nunique()
    .reset_index(name="source_count")
)

master = master.merge(
    coverage,
    how="left",
    on="universal_runner_key"
)

source_matrix = (
    master.pivot_table(
        index="universal_runner_key",
        columns="source_name",
        values="horse",
        aggfunc="count"
    )
    .fillna(0)
)

source_matrix = (source_matrix > 0).astype(int).reset_index()

master = master.merge(
    source_matrix,
    how="left",
    on="universal_runner_key"
)

master["identity_quality"] = np.where(
    master["source_count"] >= 5,
    "FULL_STACK",
    np.where(
        master["source_count"] >= 3,
        "STRONG",
        np.where(
            master["source_count"] >= 2,
            "PARTIAL",
            "WEAK"
        )
    )
)

master = (
    master
    .sort_values(
        ["source_count"],
        ascending=False
    )
    .drop_duplicates(
        ["universal_runner_key"],
        keep="first"
    )
)

master.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(master),
    "full_stack": int((master["identity_quality"] == "FULL_STACK").sum()),
    "strong": int((master["identity_quality"] == "STRONG").sum()),
    "partial": int((master["identity_quality"] == "PARTIAL").sum()),
    "weak": int((master["identity_quality"] == "WEAK").sum()),
    "avg_source_count": round(master["source_count"].mean(), 2),
    "max_source_count": int(master["source_count"].max()),
}])

diag.to_csv(DIAG, index=False)

print()
print("=" * 100)
print("IDENTITY COVERAGE")
print("=" * 100)
print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP FULL STACK RUNNERS")
print("=" * 100)

cols = [
    "track",
    "race_no",
    "horse",
    "source_count",
    "identity_quality",
]

available = [c for c in cols if c in master.columns]

print(
    master.sort_values(
        ["source_count","track","race_no"],
        ascending=[False, True, True]
    )[available]
    .head(50)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(DIAG)
