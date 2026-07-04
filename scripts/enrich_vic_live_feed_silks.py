from pathlib import Path
import pandas as pd
import re
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

LIVE_PATH = PUBLIC / "edgeiq_vic_live_terminal_feed_v1.csv"
SILKS_LOOKUP_PATH = PUBLIC / "silks_lookup.csv"
HORSE_SILKS_PATH = PUBLIC / "horse_silks.csv"
OUT_PATH = LIVE_PATH
DIAG_PATH = PUBLIC / "edgeiq_silk_enrichment_diagnostics.csv"

SILK_COLUMNS = [
    "silkUrl",
    "silk_url",
    "silks",
    "silk",
    "silk_image",
    "mobile_silk_image",
    "image",
    "runner_image",
    "tab_silk",
    "racing_silk",
    "local_silk_path",
]

def norm_key(value):
    s = str(value or "").upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = s.replace("’", "'")
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def clean_silk_path(value):
    s = str(value or "").strip()
    if not s or s.lower() in {"nan", "none", "null", "-"}:
        return ""

    s = s.replace("\\", "/")

    if s.startswith("http://") or s.startswith("https://") or s.startswith("data:"):
        return s

    s = re.sub(r"^.*?/public/", "/", s)
    s = re.sub(r"^public/", "/", s)

    if s.startswith("/"):
        return s

    if s.startswith("silks/"):
        return "/" + s

    if s.startswith("data/"):
        return "/" + s

    if s.endswith(".png") or s.endswith(".jpg") or s.endswith(".jpeg") or s.endswith(".webp") or s.endswith(".gif") or s.endswith(".svg"):
        return "/silks/" + Path(s).name

    return ""

def load_csv(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def build_lookup():
    lookup = {}

    for path in [SILKS_LOOKUP_PATH, HORSE_SILKS_PATH]:
        df = load_csv(path)
        if df.empty:
            continue

        cols = list(df.columns)
        horse_cols = [c for c in cols if c.lower() in {"horse", "horse_name", "runner", "name", "horse_key"}]
        if not horse_cols:
            horse_cols = [cols[0]]

        possible_silk_cols = [c for c in cols if c in SILK_COLUMNS or "silk" in c.lower() or "image" in c.lower() or "url" in c.lower() or "path" in c.lower()]

        for _, row in df.iterrows():
            key = norm_key(row.get(horse_cols[0], ""))
            if not key:
                continue

            silk = ""
            for c in possible_silk_cols:
                silk = clean_silk_path(row.get(c, ""))
                if silk:
                    break

            if silk:
                lookup[key] = silk

    return lookup

def main():
    live = load_csv(LIVE_PATH)
    if live.empty:
        raise SystemExit(f"Missing or empty live feed: {LIVE_PATH}")

    lookup = build_lookup()

    if "horse" not in live.columns:
        raise SystemExit("Live feed has no horse column")

    for c in SILK_COLUMNS:
        if c not in live.columns:
            live[c] = ""

    rows = []
    matched = 0

    for idx, row in live.iterrows():
        horse = row.get("horse", "")
        key = norm_key(horse)

        existing = ""
        existing_col = ""
        for c in SILK_COLUMNS:
            existing = clean_silk_path(row.get(c, ""))
            if existing:
                existing_col = c
                break

        resolved = existing or lookup.get(key, "")

        if resolved:
            matched += 1
            live.at[idx, "silkUrl"] = resolved
            live.at[idx, "silk_url"] = resolved
            live.at[idx, "local_silk_path"] = resolved

        rows.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "horse": horse,
            "horse_key": key,
            "existing_col": existing_col,
            "resolved_silk": resolved,
            "matched": "YES" if resolved else "NO",
        })

    live.to_csv(OUT_PATH, index=False, encoding="utf-8")
    pd.DataFrame(rows).to_csv(DIAG_PATH, index=False, encoding="utf-8")

    print("=" * 90)
    print("EDGEIQ SILK ENRICHMENT")
    print("=" * 90)
    print(f"LIVE ROWS: {len(live)}")
    print(f"SILK LOOKUP ROWS: {len(lookup)}")
    print(f"MATCHED SILKS: {matched}")
    print(f"UNMATCHED: {len(live) - matched}")
    print(f"UPDATED: {OUT_PATH}")
    print(f"DIAG: {DIAG_PATH}")

if __name__ == "__main__":
    main()
