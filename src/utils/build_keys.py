import pandas as pd
import re
import unicodedata


def _clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x).strip().upper()
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii")
    x = re.sub(r"\([^)]*\)", "", x)
    x = re.sub(r"[^A-Z0-9 ]+", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def build_horse_key(name):
    x = _clean_text(name)
    x = re.sub(r"[^A-Z0-9]+", "", x)
    return x


def clean_track_name(track):
    x = _clean_text(track)

    replacements = {
        "MT ": "MOUNT ",
        "ST ": "SAINT ",
    }

    for old, new in replacements.items():
        x = x.replace(old, new)

    return x.strip()


def clean_finish_pos(x):
    if pd.isna(x):
        return ""
    s = str(x).strip().upper()
    m = re.search(r"\d+", s)
    return m.group(0) if m else ""


def clean_sp(x):
    if pd.isna(x):
        return ""
    s = str(x).strip().upper()
    if s in {"", "NAN", "-", "000", "0", "0.0"}:
        return ""

    s = s.replace("$", "")
    s = re.sub(r"[^0-9\.]", "", s)

    try:
        return f"{float(s):.2f}"
    except Exception:
        return ""


def normalise_results_dataframe(df):
    df = df.copy()

    required = ["race_date", "track", "horse"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"results dataframe missing required columns: {missing}")

    df["race_date"] = pd.to_datetime(df["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["race_date"] = df["race_date"].fillna("")
    df["track_key"] = df["track"].apply(clean_track_name)
    df["horse_key"] = df["horse"].apply(build_horse_key)

    if "finish_pos" in df.columns:
        df["finish_pos_key"] = df["finish_pos"].apply(clean_finish_pos)
    else:
        df["finish_pos_key"] = ""

    if "sp" in df.columns:
        df["sp_key"] = df["sp"].apply(clean_sp)
    else:
        df["sp_key"] = ""

    df["run_match_key"] = (
        df["race_date"].astype(str)
        + "|"
        + df["track_key"].astype(str)
        + "|"
        + df["horse_key"].astype(str)
    )

    df["run_match_key_strict"] = (
        df["run_match_key"].astype(str)
        + "|"
        + df["finish_pos_key"].astype(str)
    )

    return df


def normalise_rated_runs_dataframe(df):
    df = df.copy()

    required = ["run_date", "track"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"rated runs dataframe missing required columns: {missing}")

    if "horse_key" not in df.columns and "horse" not in df.columns:
        raise ValueError("rated runs dataframe missing both horse_key and horse")

    df["race_date"] = pd.to_datetime(df["run_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["race_date"] = df["race_date"].fillna("")
    df["track_key"] = df["track"].apply(clean_track_name)

    if "horse_key" in df.columns:
        hk = df["horse_key"].fillna("").astype(str).str.strip().str.upper()
        needs_rebuild = hk.eq("")
        if "horse" in df.columns:
            rebuilt = df["horse"].apply(build_horse_key)
            df["horse_key"] = hk.where(~needs_rebuild, rebuilt)
        else:
            df["horse_key"] = hk
    else:
        df["horse_key"] = df["horse"].apply(build_horse_key)

    if "finish_pos" in df.columns:
        df["finish_pos_key"] = df["finish_pos"].apply(clean_finish_pos)
    else:
        df["finish_pos_key"] = ""

    if "starting_price" in df.columns:
        df["sp_key"] = df["starting_price"].apply(clean_sp)
    elif "sp_text" in df.columns:
        df["sp_key"] = df["sp_text"].apply(clean_sp)
    else:
        df["sp_key"] = ""

    df["run_match_key"] = (
        df["race_date"].astype(str)
        + "|"
        + df["track_key"].astype(str)
        + "|"
        + df["horse_key"].astype(str)
    )

    df["run_match_key_strict"] = (
        df["run_match_key"].astype(str)
        + "|"
        + df["finish_pos_key"].astype(str)
    )

    return df