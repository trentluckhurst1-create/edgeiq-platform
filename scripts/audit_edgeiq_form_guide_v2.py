from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"

AUDIT_TXT = DATA / "edgeiq_form_guide_v2_audit.txt"
AUDIT_JSON = DATA / "edgeiq_form_guide_v2_audit.json"

EXPECTED_COLUMNS = [
    "NO",
    "SILK",
    "LAST 5",
    "HORSE",
    "TRAINER",
    "JOCKEY",
    "WT",
    "BAR",
    "DAYS",
    "EPI",
    "MARKET",
    "EDGEiQ PRICE",
    "TRACK",
    "DIST",
    "COND",
]

PRICE_FIELDS = {
    "display_fair_price",
    "display_fair_price_governed",
    "fair_price_display",
    "ui_fair_price",
    "V6_1_RESEARCH_fair_price",
    "fair_price",
    "rated_price",
    "calibrated_price",
    "assessed_price",
    "edgeiq_price",
    "model_price",
}

MARKET_FIELDS = {
    "display_live_price",
    "live_price",
    "market_price",
    "current_price",
    "tab_fixed_win",
    "sportsbet_price",
    "fixedWin",
    "fixed_win",
    "oddsWin",
    "startingPrice",
    "market",
    "price",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.upper() in {"", "-", "NONE", "NULL", "N/A", "NA"}:
        return ""
    return text


def price(value: Any) -> str:
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return ""
    try:
        parsed = float(text)
    except ValueError:
        return ""
    if parsed <= 0 or parsed > 1000:
        return ""
    return f"${parsed:.2f}"


def parse_date(value: Any) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10])
    except ValueError:
        return None


def days_since(last_run: Any, race_date: Any) -> str:
    last = parse_date(last_run)
    race = parse_date(race_date)
    if not last or not race:
        return ""
    diff = (race - last).days
    return str(diff) if diff >= 0 else ""


def first(mapping: dict[str, Any], keys: set[str]) -> Any:
    lowered = {key.lower(): key for key in mapping.keys()}
    for key in keys:
        actual = key if key in mapping else lowered.get(key.lower())
        if actual and mapping.get(actual) not in (None, ""):
            return mapping.get(actual)
    return None


def last_run_date(source: dict[str, Any]) -> str:
    horse = source.get("horse") if isinstance(source.get("horse"), dict) else {}
    last = horse.get("lastProfessionalRaceEntryItem") if isinstance(horse.get("lastProfessionalRaceEntryItem"), dict) else {}
    race = last.get("race") if isinstance(last.get("race"), dict) else {}
    return clean(source.get("lastRunDate")) or clean(horse.get("lastRunDate")) or clean(race.get("date"))


def check(name: str, passed: bool, details: Any = "") -> dict[str, Any]:
    return {
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }


def main() -> int:
    component = read(COMPONENT)
    normaliser = read(NORMALISER)
    css = read(CSS)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}

    column_match = re.search(r"const summaryColumns = \[(.*?)\];", component, re.S)
    columns = re.findall(r'"([^"]+)"', column_match.group(1)) if column_match else []
    runners: list[dict[str, Any]] = []

    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            race_date = meeting.get("date")
            for runner in race.get("runners", []):
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                last_five = official.get("lastFive") or []
                market = price(official.get("market")) or price(first(source, MARKET_FIELDS))
                edgeiq = price(first(official, PRICE_FIELDS)) or price(first(source, PRICE_FIELDS))
                latest = last_run_date(source)
                runners.append(
                    {
                        "official": official,
                        "source": source,
                        "race_date": race_date,
                        "last_five_count": len(last_five) if isinstance(last_five, list) else 0,
                        "days": days_since(latest, race_date),
                        "market": market if not official.get("scratched") else "",
                        "edgeiq_price": edgeiq if not official.get("scratched") else "",
                        "epi": clean(source.get("projected_rating_v5_2"))
                        or clean(source.get("projected_rating_V6_1_RESEARCH"))
                        or clean(source.get("total_rating_points")),
                    }
                )

    invalid_prices_suppressed = sum(
        1
        for runner in runners
        for value in [
            first(runner["official"], PRICE_FIELDS),
            first(runner["source"], PRICE_FIELDS),
            runner["official"].get("market"),
        ]
        if clean(value) and not price(value)
    )

    counts = {
        "runners": len(runners),
        "first_starters": sum(1 for runner in runners if runner["last_five_count"] == 0),
        "runners_with_days": sum(1 for runner in runners if runner["days"]),
        "runners_with_market": sum(1 for runner in runners if runner["market"]),
        "runners_with_edgeiq_price": sum(1 for runner in runners if runner["edgeiq_price"]),
        "runners_with_epi": sum(1 for runner in runners if runner["epi"]),
        "scratched_runners": sum(1 for runner in runners if runner["official"].get("scratched")),
        "invalid_prices_suppressed": invalid_prices_suppressed,
    }

    checks = [
        check("component exists", COMPONENT.exists(), str(COMPONENT)),
        check("normaliser exists", NORMALISER.exists(), str(NORMALISER)),
        check("expanded desktop width", "width: min(1380px, 100%)" in css and "max-width: calc(100vw - 260px)" in css),
        check("table typography increased", "font-size: 12.5px" in css and "font-size: 14px" in css),
        check("silk size increased", "width: 38px" in css and "height: 38px" in css),
        check("last five tile size increased", "min-width: 22px" in css and "height: 26px" in css),
        check("correct column order", columns == EXPECTED_COLUMNS, "|".join(columns)),
        check("DAYS column exists", "DAYS" in columns and "Days since last official start" in component),
        check("MARKET column exists", "MARKET" in columns),
        check("EDGEiQ PRICE column exists", "EDGEiQ PRICE" in columns and "EDGEiQ assessed price" in component),
        check("EPI remains", "EPI" in columns),
        check("TRACK DIST COND remain", all(item in columns for item in ["TRACK", "DIST", "COND"])),
        check("days uses selected race date", "calculateDaysSinceLastRun(latestRunDate(runner), date)" in normaliser),
        check("first starters blank days", "if (!last || !race) return \"\"" in normaliser),
        check("negative days suppressed", "diff < 0" in normaliser),
        check("market uses canonical field list", "MARKET_PRICE_FIELDS" in normaliser and "startingPrice" in normaliser),
        check("EDGEiQ price uses canonical field list", "EDGEIQ_PRICE_FIELDS" in normaliser and "V6_1_RESEARCH_fair_price" in normaliser),
        check("market and EDGEiQ price not same field", "MARKET_PRICE_FIELDS" in normaliser and "EDGEIQ_PRICE_FIELDS" in normaliser and MARKET_FIELDS.isdisjoint(PRICE_FIELDS)),
        check("pricing logic not implemented in JSX", "formatPrice" not in component and "EDGEIQ_PRICE_FIELDS" not in component),
        check("no new pricing formula in normaliser", "1 /" not in normaliser and "probability" not in normaliser.lower()),
        check("invalid price values hidden", "parsed <= 0" in normaliser and "parsed > 1000" in normaliser and "Number.isFinite" in normaliser),
        check("no tipping language in form guide", not re.search(r"\b(BET|BACK|LAY|TIP|WATCH|SELECTION|DECISION)\b", component, re.I)),
        check("no raw JSON rendering", "JSON.stringify" not in component and "[object Object]" not in component),
        check("runner selection still works", "setSelectedRunnerId" in component and "scrollToRunner" in component),
        check("full form section still works", "eiq-form-runner-detail" in component and "FULL FORM" in component),
        check("race navigation still works", "onOpenRace" in component and "Race selector" in component),
        check("MARKET tab still present", '"MARKET"' in read(ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx")),
        check("MAP tab still present", '"MAP"' in read(ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx")),
        check("OVERVIEW tab still present", '"OVERVIEW"' in read(ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx")),
        check("catalog rows available", counts["runners"] > 0, counts),
    ]

    passed = all(item["status"] == "PASS" for item in checks)
    status = "EDGEIQ_FORM_GUIDE_V2_AUDIT_PASS" if passed else "EDGEIQ_FORM_GUIDE_V2_AUDIT_FAIL"
    payload = {
        "status": status,
        "generated_at": datetime.now().isoformat(),
        "counts": counts,
        "checks": checks,
        "data_wiring": {
            "last_run_date": "source.horse.lastProfessionalRaceEntryItem.race.date, or canonical lastRunDate when present",
            "days_since_last_run": "calculateDaysSinceLastRun(lastRunDate, selected race date)",
            "epi": "projected_rating_v5_2 / projected_rating_V6_1_RESEARCH / total_rating_points when present",
            "market_price": "official.market / display_live_price / live_price / market_price / current_price / oddsWin / startingPrice",
            "edgeiq_price": "display_fair_price / display_fair_price_governed / fair_price_display / ui_fair_price / V6_1_RESEARCH_fair_price / fair_price / rated_price / calibrated_price",
            "track_record": "source.horse.stats matching selected track when labelled by source",
            "distance_record": "source.horse.stats matching selected distance when labelled by source",
            "condition_record": "source.horse.stats matching selected condition when labelled by source",
        },
    }

    DATA.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    AUDIT_TXT.write_text(
        "\n".join(
            [
                status,
                f"generated_at={payload['generated_at']}",
                f"counts={json.dumps(counts, sort_keys=True)}",
                "",
                *[f"{item['status']} | {item['check']} | {item['details']}" for item in checks],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(status)
    print(json.dumps(counts, sort_keys=True))
    print(f"audit_txt={AUDIT_TXT}")
    print(f"audit_json={AUDIT_JSON}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
