import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def num(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw or raw.upper() in {"NA", "N/A", "--", "NULL", "NONE"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def first_num(row: dict[str, str], keys: list[str]) -> float | None:
    for key in keys:
        value = num(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def race_date(row: dict[str, str]) -> str:
    return text(row.get("race_date") or row.get("current_race_date") or row.get("meeting_date") or row.get("date") or row.get("_date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number") or row.get("race") or row.get("_race"))


def horse_key(row: dict[str, str]) -> str:
    return clean(row.get("horse_key") or row.get("horse"))


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (race_date(row), clean(row.get("track") or row.get("_track")), race_no(row))


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (*race_key(row), horse_key(row))


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "TRUE", "1", "Y"}


def production_probability(row: dict[str, str]) -> float | None:
    value = first_num(row, ["win_pct", "V6_1_RESEARCH_probability", "probability_normalised_v1", "rated_probability"])
    if value is None:
        price = production_fair_price(row)
        return 1 / price if price and price > 0 else None
    if value > 1:
        value = value / 100
    return max(0.0, min(1.0, value))


def production_fair_price(row: dict[str, str]) -> float | None:
    return first_num(row, ["display_fair_price", "ui_fair_price", "fair_price", "rated_price", "V6_1_RESEARCH_fair_price"])


def market_price(row: dict[str, str]) -> float | None:
    return first_num(row, ["live_price", "tab_fixed_win", "display_live_price", "market_price", "fixed_odds", "win_odds", "sp", "closing_price"])


def rating(row: dict[str, str]) -> float | None:
    return first_num(row, ["total_rating_points", "projected_rating_V6_1_RESEARCH", "projected_rating_v5_2", "adjusted_rating", "latest_flat_rating"])


def confidence_score(row: dict[str, str]) -> float:
    raw = text(row.get("projection_confidence_v5_2") or row.get("projection_band_v5_2") or row.get("projection_band_V6_1_RESEARCH")).upper()
    mapped = {
        "ELITE": 95,
        "HIGH": 85,
        "STRONG": 80,
        "POSITIVE": 70,
        "MEDIUM": 60,
        "MODERATE": 55,
        "NEUTRAL": 50,
        "LOW": 35,
        "LIMITED": 30,
        "WEAK": 25,
    }
    for token, value in mapped.items():
        if token in raw:
            return float(value)
    return first_num(row, ["confidence_score", "projection_confidence_v5_2", "map_confidence"]) or 50.0


def by_race(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    grouped: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[race_key(row)].append(row)
    return dict(grouped)


def entropy_ratio(probs: list[float]) -> float:
    values = [p for p in probs if p > 0]
    total = sum(values)
    if len(values) < 2 or total <= 0:
        return 0.0
    norm = [p / total for p in values]
    return -sum(p * math.log(p) for p in norm) / math.log(len(values))


def hhi(probs: list[float]) -> float:
    total = sum(probs)
    if total <= 0:
        return 0.0
    return sum((p / total) ** 2 for p in probs if p > 0)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median_value(values: list[float]) -> float:
    return float(median(values)) if values else 0.0


def bucket_field_size(size: int) -> str:
    if size <= 7:
        return "SMALL_1_7"
    if size <= 10:
        return "MEDIUM_8_10"
    if size <= 14:
        return "LARGE_11_14"
    return "MAX_15_PLUS"


def bucket_distance(value: object) -> str:
    distance = first_num({"distance": text(value)}, ["distance"]) or 0
    if distance <= 0:
        return "UNKNOWN"
    if distance < 1200:
        return "SPRINT_LT1200"
    if distance < 1600:
        return "SPRINT_MILE_1200_1599"
    if distance < 2000:
        return "MIDDLE_1600_1999"
    return "STAYING_2000_PLUS"


def bucket_price(price: float) -> str:
    if price < 2:
        return "LT_2"
    if price < 3:
        return "2_TO_3"
    if price < 4:
        return "3_TO_4"
    if price < 5:
        return "4_TO_5"
    if price < 6:
        return "5_TO_6"
    return "6_PLUS"


def classify_shape(fav_price: float, top_prob: float, top3: float, entropy: float) -> str:
    if fav_price <= 0 or top_prob <= 0:
        return "UNKNOWN"
    if fav_price >= 5 or top_prob < 0.22 or entropy > 0.88:
        return "COMPRESSED"
    if fav_price < 2.2 or top_prob > 0.45 or top3 > 0.78 or entropy < 0.55:
        return "OVER_CONCENTRATED"
    return "HEALTHY"


def format_float(value: float | None, digits: int = 4) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"
