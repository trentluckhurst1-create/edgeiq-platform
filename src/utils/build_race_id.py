import pandas as pd
import re


def clean_text(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\s+", " ", x)
    x = re.sub(r"[^A-Z0-9 ]", "", x)
    return x.strip()


def clean_track(track):
    track = clean_text(track)

    # Optional normalisations (expand later if needed)
    replacements = {
        "MT": "MOUNT",
        "ST": "SAINT",
    }

    for k, v in replacements.items():
        track = track.replace(k, v)

    return track


def clean_race_name(name):
    name = clean_text(name)

    # Remove common noise
    remove_words = [
        "HANDICAP",
        "PLATE",
        "STAKES",
        "CLASS",
        "GROUP",
        "LISTED",
    ]

    for word in remove_words:
        name = name.replace(word, "")

    return name.strip()


def clean_distance(dist):
    if pd.isna(dist):
        return ""

    try:
        return str(int(float(dist)))
    except:
        return ""


def build_race_id(df):
    df = df.copy()

    df["race_date"] = df["race_date"].astype(str)
    df["track"] = df["track"].apply(clean_track)
    df["race_name"] = df["race_name"].apply(clean_race_name)
    df["distance"] = df["distance"].apply(clean_distance)

    df["race_id"] = (
        df["race_date"]
        + "_"
        + df["track"]
        + "_"
        + df["race_name"]
        + "_"
        + df["distance"]
    )

    return df