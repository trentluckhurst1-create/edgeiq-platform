from __future__ import annotations

import math
import re

import pandas as pd


BRANDING_PREFIXES = [
    "BET365 ",
    "LADBROKES ",
    "SPORTSBET ",
    "SPORTSBET-",
    "APIAM ",
    "SOUTHSIDE ",
    "PICKLEBET PARK ",
    "BET365 PARK ",
    "THE EXCHANGE ",
]

STATIC_TRACK_ALIASES = {
    "BDLE": "BAIRNSDALE",
    "WNBL": "WARRNAMBOOL",
    "PAKM": "PAKENHAM",
    "PAKS": "PAKENHAM SYNTHETIC",
    "WANG": "WANGARATTA",
    "SEYM": "SEYMOUR",
    "BDGO": "BENDIGO",
    "ECHA": "ECHUCA",
    "WMAI": "WOOLAMAI",
    "HTON": "HAMILTON",
    "CAUL": "CAULFIELD",
    "FLEM": "FLEMINGTON",
    "GEEL": "GEELONG",
    "KILM": "PARK KILMORE",
    "KYNE": "PARK KYNETON",
    "WOD": "WODONGA",
    "CAST": "CASTERTON",
    "STAW": "STAWELL",
    "MORN": "MORNINGTON",
    "CRAN": "CRANBOURNE",
    "SANL": "SANDOWN LAKESIDE",
    "SANH": "SANDOWN HILLSIDE",
    "BRAT": "BALLARAT",
    "BRTS": "BALLARAT SYN",
    "M V": "THE VALLEY",
    "MV": "THE VALLEY",
    "Y VL": "YARRA VALLEY",
    "YVL": "YARRA VALLEY",
    "WERR": "WERRIBEE",
    "ALEX": "ALEXANDRA",
    "ARAT": "ARARAT",
    "CAMP": "CAMPERDOWN",
    "COLR": "COLERAINE",
    "MILD": "MILDURA",
    "HEAL": "HEALESVILLE",
    "EHPE": "EDENHOPE",
    "DDRG": "DEDERANG",
    "TOW": "TOWONG",
    "TER": "TERANG",
    "KRNG": "KERANG",
    "BLLA": "BENALLA",
    "HSHM": "HORSHAM",
    "S CK": "STONY CREEK",
    "SCK": "STONY CREEK",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def canon_horse(value: object) -> str:
    text = upper(value).replace("Ã¢â‚¬â„¢", "'").replace("â€™", "'").replace("’", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def compact_token(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", upper(value))


def base_track_name(value: object) -> str:
    text = upper(value).replace("-", " ")
    for prefix in BRANDING_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = re.sub(r"\s+", " ", text).strip()
    if text.endswith(" PICNIC"):
        text = text[: -len(" PICNIC")].strip()
    return text


def candidate_track_keys(value: object) -> list[str]:
    raw = upper(value).replace("-", " ")
    base = base_track_name(value)
    keys = []
    for key in [raw, base, compact_token(raw), compact_token(base)]:
        key = clean(key)
        if key != "" and key not in keys:
            keys.append(key)
    return keys


def apply_track_alias(value: object, alias_map: dict[str, str] | None = None) -> str:
    alias_map = alias_map or {}
    for key in candidate_track_keys(value):
        if key in alias_map and clean(alias_map[key]) != "":
            return clean(alias_map[key])
    base = base_track_name(value)
    return base


def build_track_alias_bridge(
    settled_frame: pd.DataFrame,
    back_frame: pd.DataFrame,
    min_pair_rows: int = 2,
) -> tuple[dict[str, str], pd.DataFrame]:
    settled = settled_frame.copy()
    back = back_frame.copy()

    settled["bridge_meeting_date_v1"] = settled["meeting_date"].map(clean).str[:10]
    settled["bridge_horse_key_v1"] = settled["horse_key"].where(
        settled["horse_key"].map(clean).ne(""),
        settled["horse"].map(canon_horse),
    ).map(canon_horse)
    settled["bridge_track_canonical_v1"] = settled["track"].map(base_track_name)
    settled["bridge_join_v1"] = settled["bridge_meeting_date_v1"] + "|" + settled["bridge_horse_key_v1"]

    back_date_col = "meeting_date" if "meeting_date" in back.columns else "race_date"
    back_horse_col = "horse_key" if "horse_key" in back.columns else "horse"
    back_track_col = "track"
    back["bridge_meeting_date_v1"] = back[back_date_col].map(clean).str[:10]
    back["bridge_horse_key_v1"] = back[back_horse_col].map(canon_horse)
    back["bridge_track_raw_v1"] = back[back_track_col].map(upper)
    back["bridge_track_base_v1"] = back[back_track_col].map(base_track_name)
    back["bridge_join_v1"] = back["bridge_meeting_date_v1"] + "|" + back["bridge_horse_key_v1"]

    settled_counts = settled["bridge_join_v1"].value_counts()
    back_counts = back["bridge_join_v1"].value_counts()
    settled = settled[settled["bridge_join_v1"].map(settled_counts).eq(1)].copy()
    back = back[back["bridge_join_v1"].map(back_counts).eq(1)].copy()

    merged = settled[
        ["bridge_join_v1", "track", "bridge_track_canonical_v1"]
    ].merge(
        back[
            ["bridge_join_v1", "bridge_track_raw_v1", "bridge_track_base_v1"]
        ],
        on="bridge_join_v1",
        how="inner",
    )

    pair_rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        canonical = clean(row["bridge_track_canonical_v1"])
        if canonical == "":
            continue
        for alias_candidate in [row["bridge_track_raw_v1"], row["bridge_track_base_v1"]]:
            alias_candidate = clean(alias_candidate)
            if alias_candidate == "":
                continue
            pair_rows.append(
                {
                    "alias_key": alias_candidate,
                    "canonical_track": canonical,
                    "source": "DYNAMIC_PAIR",
                }
            )
            compact_alias = compact_token(alias_candidate)
            if compact_alias != "" and compact_alias != alias_candidate:
                pair_rows.append(
                    {
                        "alias_key": compact_alias,
                        "canonical_track": canonical,
                        "source": "DYNAMIC_PAIR_COMPACT",
                    }
                )

    pair_df = pd.DataFrame(pair_rows)
    if pair_df.empty:
        dynamic_choice = pd.DataFrame(columns=["alias_key", "canonical_track", "rows", "second_rows", "chosen"])
    else:
        counts = (
            pair_df.groupby(["alias_key", "canonical_track", "source"], dropna=False)
            .size()
            .reset_index(name="rows")
        )
        chosen_rows: list[dict[str, object]] = []
        for alias_key, group in counts.groupby("alias_key", dropna=False):
            group = group.sort_values(["rows", "canonical_track"], ascending=[False, True]).reset_index(drop=True)
            top = group.iloc[0]
            second_rows = int(group.iloc[1]["rows"]) if len(group) > 1 else 0
            chosen_flag = (
                int(top["rows"]) >= min_pair_rows
                and int(top["rows"]) > second_rows
                and clean(alias_key) != clean(top["canonical_track"])
            )
            chosen_rows.append(
                {
                    "alias_key": clean(alias_key),
                    "canonical_track": clean(top["canonical_track"]),
                    "rows": int(top["rows"]),
                    "second_rows": second_rows,
                    "source": clean(top["source"]),
                    "chosen": "YES" if chosen_flag else "NO",
                }
            )
        dynamic_choice = pd.DataFrame(chosen_rows)

    alias_map: dict[str, str] = {}
    audit_rows: list[dict[str, object]] = []

    for alias_key, canonical in STATIC_TRACK_ALIASES.items():
        alias_map[clean(alias_key)] = clean(canonical)
        audit_rows.append(
            {
                "alias_key": clean(alias_key),
                "canonical_track": clean(canonical),
                "rows": None,
                "second_rows": None,
                "source": "STATIC_SEED",
                "chosen": "YES",
            }
        )

    if not dynamic_choice.empty:
        for _, row in dynamic_choice.iterrows():
            audit_rows.append(
                {
                    "alias_key": clean(row["alias_key"]),
                    "canonical_track": clean(row["canonical_track"]),
                    "rows": row["rows"],
                    "second_rows": row["second_rows"],
                    "source": clean(row["source"]),
                    "chosen": clean(row["chosen"]),
                }
            )
            if clean(row["chosen"]) == "YES":
                alias_map[clean(row["alias_key"])] = clean(row["canonical_track"])

    audit_df = pd.DataFrame(audit_rows)
    if not audit_df.empty:
        audit_df = audit_df.sort_values(
            ["chosen", "rows", "alias_key"],
            ascending=[False, False, True],
            na_position="last",
        ).reset_index(drop=True)

    return alias_map, audit_df
