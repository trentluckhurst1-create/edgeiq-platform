from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception:
    sync_playwright = None
    PlaywrightTimeoutError = Exception


BASE_DIR = Path(__file__).resolve().parent

DEFAULT_FIELDS = BASE_DIR / "data" / "upcoming" / "race_fields.csv"
DEFAULT_OUT = BASE_DIR / "outputs" / "markets" / "market_odds_report.csv"
DEFAULT_VALIDATION = BASE_DIR / "outputs" / "markets" / "market_odds_validation.csv"
DEFAULT_DEBUG = BASE_DIR / "outputs" / "markets" / "market_odds_debug.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

BOOKMAKER_PREFIXES = ["bet365", "sportsbet", "ladbrokes", "tab", "neds"]


def normalize_text(x: Any) -> str:
    return str(x or "").strip()


def normalize_date_string(x: Any) -> str:
    s = normalize_text(x)
    dt = pd.to_datetime(s, errors="coerce")
    if pd.isna(dt):
        return s[:10]
    return dt.strftime("%Y-%m-%d")


def normalize_track_name(name: str) -> str:
    s = normalize_text(name).upper()
    s = re.sub(r"^(BET365|SPORTSBET|LADBROKES|TAB|NEDS)\s+", "", s)
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def slugify_track_for_url(name: str) -> str:
    s = normalize_text(name).lower()
    s = re.sub(r"^(bet365|sportsbet|ladbrokes|tab|neds)\s+", "", s)
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def normalize_horse_name(name: str) -> str:
    s = normalize_text(name).upper()
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_horse_key(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", normalize_horse_name(name))


def clean_market_price(x: Any) -> Optional[float]:
    try:
        v = float(str(x).replace("$", "").replace(",", "").strip())
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    if v <= 1.01 or v > 1000:
        return None
    return v


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def walk(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def find_best_price_in_obj(root: Any) -> Optional[float]:
    best: Optional[float] = None

    for node in walk(root):
        if not isinstance(node, dict):
            continue

        vals: List[Any] = []

        for key in ["fixedOdds", "fixed_odds", "price", "winPrice", "win_price", "odds", "decimalPrice", "decimal_price", "bestPrice", "best_price", "currencyValue", "value"]:
            if key in node:
                vals.append(node.get(key))

        # prefer explicit win bet type if present
        bet_type = str(node.get("betType") or node.get("bet_type") or node.get("betTypeKebab") or "").lower()
        display_name = str(node.get("displayName") or node.get("name") or "").lower()
        if bet_type and "win" not in bet_type and display_name and "win" not in display_name:
            # still allow raw price fallback, but only if no better explicit one appears later
            pass

        for raw in vals:
            price = clean_market_price(raw)
            if price is None:
                continue
            if best is None or price > best:
                best = price

    return best


def candidate_name_from_obj(node: dict) -> str:
    for key in [
        "horseName", "horse_name", "runnerName", "runner_name", "name", "displayName",
        "competitorName", "competitor_name", "selectionName", "selection_name",
    ]:
        val = node.get(key)
        if isinstance(val, str) and normalize_text(val):
            return normalize_text(val)
    return ""


def extract_runner_prices_from_json(root: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}

    for node in walk(root):
        if not isinstance(node, dict):
            continue

        name = candidate_name_from_obj(node)
        if not name:
            continue

        price = find_best_price_in_obj(node)
        if price is None:
            continue

        key = build_horse_key(name)
        if not key:
            continue

        existing = out.get(key)
        if existing is None or price > existing:
            out[key] = price

    return out


def extract_json_blobs_from_html(html: str) -> List[Any]:
    blobs: List[Any] = []

    patterns = [
        r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>',
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        r'window\.__NUXT__\s*=\s*(\{.*?\})\s*;</script>',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;</script>',
    ]

    for pat in patterns:
        for m in re.finditer(pat, html, flags=re.S | re.I):
            raw = m.group(1).strip()
            if not raw:
                continue
            try:
                blobs.append(json.loads(raw))
            except Exception:
                pass

    return blobs


def discover_race_urls(page, meeting_slug: str) -> List[str]:
    meeting_url = f"https://www.punters.com.au/form-guide/horses/{meeting_slug}/"
    page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)

    hrefs = page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => e.href).filter(Boolean)"
    )

    urls = []
    for href in hrefs:
        if "/form-guide/horses/" not in href:
            continue
        if "-race-" not in href:
            continue
        href = href.split("#")[0].split("?")[0]
        if not href.endswith("/"):
            href += "/"
        urls.append(href)

    return sorted(set(urls))


def parse_race_no_from_url(url: str) -> Optional[int]:
    m = re.search(r"-race-(\d+)/?$", url)
    return int(m.group(1)) if m else None


def extract_prices_from_race_page(page, url: str) -> Tuple[Dict[str, float], Dict[str, Any]]:
    debug: Dict[str, Any] = {"url": url, "methods": []}
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)

    html = page.content()

    # Method 1: pull JSON blobs from page and infer runner prices
    prices: Dict[str, float] = {}
    blobs = extract_json_blobs_from_html(html)
    debug["methods"].append({"json_blobs_found": len(blobs)})

    for blob in blobs:
        found = extract_runner_prices_from_json(blob)
        for k, v in found.items():
            if k not in prices or v > prices[k]:
                prices[k] = v

    # Method 2: visible DOM fallback for likely odds cells
    if len(prices) == 0:
        text = page.locator("body").inner_text(timeout=10000)
        debug["methods"].append({"body_text_len": len(text)})

    debug["prices_found"] = len(prices)
    sample = list(prices.items())[:10]
    debug["sample"] = sample

    return prices, debug


def load_fields(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "race_date" not in df.columns and "date" in df.columns:
        df["race_date"] = df["date"]
    if "race_no" not in df.columns and "race_number" in df.columns:
        df["race_no"] = df["race_number"]

    required = ["race_date", "track", "race_no", "horse"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"race_fields.csv missing columns: {missing}")

    df["race_date"] = df["race_date"].apply(normalize_date_string)
    df["track"] = df["track"].astype(str).str.strip()
    df["track_key"] = df["track"].apply(normalize_track_name)
    df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
    df["horse"] = df["horse"].astype(str).str.strip()
    df["horse_key"] = df["horse"].apply(build_horse_key)
    return df


def build_race_refs(fields_df: pd.DataFrame) -> pd.DataFrame:
    refs = (
        fields_df[["race_date", "track", "track_key", "race_no"]]
        .drop_duplicates()
        .sort_values(["race_date", "track", "race_no"])
        .reset_index(drop=True)
    )
    refs["meeting_slug"] = refs.apply(
        lambda r: f"{slugify_track_for_url(r['track'])}-{str(r['race_date']).replace('-', '')}",
        axis=1,
    )
    return refs


def build_output_rows(fields_df: pd.DataFrame, all_prices: Dict[Tuple[str, str, int], Dict[str, float]], debug_blob: List[Dict[str, Any]]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for _, row in fields_df.iterrows():
        key = (row["race_date"], row["track_key"], int(row["race_no"]))
        race_prices = all_prices.get(key, {})
        market_price = race_prices.get(row["horse_key"])
        market_price = clean_market_price(market_price)

        rows.append({
            "race_date": row["race_date"],
            "track": row["track"],
            "race_no": int(row["race_no"]),
            "horse": row["horse"],
            "horse_key": row["horse_key"],
            "market_price": market_price,
        })

    out = pd.DataFrame(rows)
    out = out.sort_values(["race_date", "track", "race_no", "horse"]).reset_index(drop=True)
    return out


def build_validation(fields_df: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    base = (
        fields_df.groupby(["race_date", "track", "race_no"], dropna=False)
        .size()
        .reset_index(name="field_size")
    )
    cov = (
        out_df[out_df["market_price"].notna()]
        .groupby(["race_date", "track", "race_no"], dropna=False)
        .size()
        .reset_index(name="priced_runners")
    )
    val = base.merge(cov, on=["race_date", "track", "race_no"], how="left")
    val["priced_runners"] = val["priced_runners"].fillna(0).astype(int)
    val["coverage_pct"] = (val["priced_runners"] / val["field_size"] * 100).round(1)
    return val.sort_values(["race_date", "track", "race_no"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite Punters market odds scraper using Playwright.")
    parser.add_argument("--fields", default=str(DEFAULT_FIELDS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--validation-out", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--debug-json-out", default=str(DEFAULT_DEBUG))
    parser.add_argument("--race-date", default=None)
    parser.add_argument("--track", default=None)
    parser.add_argument("--max-races", type=int, default=None)
    parser.add_argument("--headless", action="store_true", default=False)
    return parser.parse_args()


def main() -> None:
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright is not installed. Install with: pip install playwright\n"
            "Then run: python -m playwright install chromium"
        )

    args = parse_args()

    fields_path = Path(args.fields)
    out_path = Path(args.out)
    validation_path = Path(args.validation_out)
    debug_path = Path(args.debug_json_out)

    ensure_parent(out_path)
    ensure_parent(validation_path)
    ensure_parent(debug_path)

    fields_df = load_fields(fields_path)

    if args.race_date:
        fields_df = fields_df[fields_df["race_date"] == normalize_date_string(args.race_date)].copy()
    if args.track:
        fields_df = fields_df[fields_df["track"].str.lower() == str(args.track).lower()].copy()

    if fields_df.empty:
        raise RuntimeError("No race fields found after filters.")

    race_refs = build_race_refs(fields_df)
    if args.max_races:
        race_refs = race_refs.head(args.max_races)

    all_prices: Dict[Tuple[str, str, int], Dict[str, float]] = {}
    debug_blob: List[Dict[str, Any]] = []

    print("=== SCRAPE PUNTERS MARKET ODDS (PLAYWRIGHT REWRITE) ===")
    print(f"Race fields: {fields_path}")
    print(f"Unique races: {len(race_refs)}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1400, "height": 1200})
        page = context.new_page()

        for idx, race in race_refs.iterrows():
            meeting_slug = race["meeting_slug"]
            race_date = race["race_date"]
            track = race["track"]
            track_key = race["track_key"]
            race_no = int(race["race_no"])

            print(f"\n[{idx+1}/{len(race_refs)}] {track} {race_date} R{race_no}")

            race_debug: Dict[str, Any] = {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "meeting_slug": meeting_slug,
            }

            try:
                urls = discover_race_urls(page, meeting_slug)
                race_debug["race_urls_found"] = len(urls)
                target_url = None
                for url in urls:
                    if parse_race_no_from_url(url) == race_no:
                        target_url = url
                        break

                race_debug["target_url"] = target_url

                if not target_url:
                    print("  no race url found")
                    debug_blob.append(race_debug)
                    continue

                prices, page_debug = extract_prices_from_race_page(page, target_url)
                race_debug["page_debug"] = page_debug

                all_prices[(race_date, track_key, race_no)] = prices
                print(f"  prices found: {len(prices)}")

            except PlaywrightTimeoutError as exc:
                race_debug["error"] = f"timeout: {exc}"
                print(f"  timeout")
            except Exception as exc:
                race_debug["error"] = str(exc)
                print(f"  failed: {exc}")

            debug_blob.append(race_debug)

        browser.close()

    out_df = build_output_rows(fields_df, all_prices, debug_blob)
    validation_df = build_validation(fields_df, out_df)

    out_df.to_csv(out_path, index=False)
    validation_df.to_csv(validation_path, index=False)
    debug_path.write_text(json.dumps(debug_blob, indent=2), encoding="utf-8")

    total = len(out_df)
    priced = int(out_df["market_price"].notna().sum())
    coverage = round(priced / total * 100, 1) if total else 0.0

    print("\n=== DONE ===")
    print(f"Wrote: {out_path}")
    print(f"Wrote: {validation_path}")
    print(f"Wrote: {debug_path}")
    print(f"Coverage: {priced}/{total} = {coverage}%")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nFATAL: {exc}")
        sys.exit(1)
