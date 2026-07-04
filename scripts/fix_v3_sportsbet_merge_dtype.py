from pathlib import Path

path = Path(r".\scripts\build_edgeiq_probability_engine_v3.py")
text = path.read_text(encoding="utf-8")

old = '''def merge_sportsbet_prices_direct(live):
    sports = read_csv(SPORTSBET)
    if live.empty or sports.empty:
        return live

    left = live.copy()
    right = sports.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    right["sportsbet_price_direct"] = right.get("sportsbet_price", "").astype(str).str.strip()
    right = (
        right[["_key", "sportsbet_price_direct"]]
        .drop_duplicates("_key", keep="last")
    )

    merged = left.merge(right, on="_key", how="left")

    price = merged["sportsbet_price_direct"].astype(str).str.strip()
    has_price = price.ne("") & price.ne("nan") & price.ne("0") & price.ne("0.0")

    for col in ["sportsbet_price", "market_price", "live_price", "current_price"]:
        if col not in merged.columns:
            merged[col] = ""
        merged.loc[has_price, col] = price[has_price]

    return merged.drop(columns=["_key", "sportsbet_price_direct"], errors="ignore")
'''

new = '''def merge_sportsbet_prices_direct(live):
    sports = read_csv(SPORTSBET)
    if live.empty or sports.empty:
        return live

    left = live.copy()
    right = sports.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    right["sportsbet_price_direct"] = pd.to_numeric(right.get("sportsbet_price", ""), errors="coerce")
    right = (
        right[["_key", "sportsbet_price_direct"]]
        .dropna(subset=["sportsbet_price_direct"])
        .drop_duplicates("_key", keep="last")
    )

    merged = left.merge(right, on="_key", how="left")

    price = pd.to_numeric(merged["sportsbet_price_direct"], errors="coerce")
    has_price = price.notna() & (price > 1)

    for col in ["sportsbet_price", "market_price", "live_price", "current_price"]:
        if col not in merged.columns:
            merged[col] = pd.NA
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
        merged.loc[has_price, col] = price.loc[has_price].astype(float)

    return merged.drop(columns=["_key", "sportsbet_price_direct"], errors="ignore")
'''

if old not in text:
    raise SystemExit("merge_sportsbet_prices_direct block not found")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("fixed merge_sportsbet_prices_direct dtype handling")
