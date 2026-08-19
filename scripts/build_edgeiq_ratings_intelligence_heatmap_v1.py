import csv
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_ratings_intelligence_heatmap_v1.csv"
SUMMARY = DATA / "edgeiq_ratings_intelligence_heatmap_v1_summary.csv"
REPORT = DATA / "edgeiq_ratings_intelligence_heatmap_v1_report.txt"

SOURCES = {
    "governed": DATA / "edgeiq_live_runner_board_governed_v1.csv",
    "factor_lab": DATA / "edgeiq_factor_lab_enrichment_feed_v1.csv",
    "factor_scorecard": DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
    "runner_enrichment": DATA / "edgeiq_runners_enrichment_feed_v1_1.csv",
    "connection": DATA / "edgeiq_connection_intelligence_v2_1.csv",
    "campaign": DATA / "edgeiq_campaign_feed_v1.csv",
    "command": DATA / "edgeiq_command_enrichment_feed_v3.csv",
}

FIELDNAMES = [
    "race_date", "track", "race_no", "race_key", "runner_key", "horse", "horse_key",
    "runner_rating", "runner_rating_source", "expected_rating", "expected_rating_source", "rating_gap",
    "distance_heat", "condition_heat", "class_heat", "campaign_heat", "connections_heat",
    "distance_score", "condition_score", "class_score", "campaign_score", "connections_score",
    "overall_heat_score", "heat_band", "heat_colour_intent", "evidence_status", "source_trace",
]


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def text(value):
    if value is None:
        return ""
    return str(value).strip()


def clean_track(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def clean_horse(value):
    s = text(value).upper()
    while "(" in s and ")" in s:
        start = s.find("(")
        end = s.find(")", start)
        if end < 0:
            break
        s = s[:start] + s[end + 1:]
    return "".join(ch for ch in s if ch.isalnum())


def race_no(row):
    s = text(row.get("race_no") or row.get("raceNo") or row.get("race_number"))
    return s.upper().replace("R", "")


def race_date(row):
    return text(row.get("race_date") or row.get("current_race_date") or row.get("date"))


def horse_name(row):
    return text(row.get("horse") or row.get("runner_name") or row.get("horse_name"))


def key(row):
    return "|".join([
        race_date(row),
        clean_track(row.get("track")),
        race_no(row),
        clean_horse(row.get("horse_key") or horse_name(row)),
    ])


def race_key(row):
    return "|".join([race_date(row), clean_track(row.get("track")), race_no(row)])


def to_float(value):
    s = text(value).replace("$", "").replace(",", "").replace("%", "")
    if not s or s.upper() in {"-", "NA", "N/A", "NULL", "NONE", "UNKNOWN", "NOT LOADED", "SOURCE GAP"}:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    if not math.isfinite(n):
        return None
    return n


def first_num(row, cols):
    for col in cols:
        if col in row:
            n = to_float(row.get(col))
            if n is not None:
                return n, col
    return None, ""


def fmt_num(value):
    if value is None:
        return ""
    return f"{value:.1f}".rstrip("0").rstrip(".")


def heat_label(score):
    if score is None:
        return "NO_EVIDENCE"
    if score >= 70:
        return "STRONG"
    if score >= 55:
        return "POSITIVE"
    if score >= 45:
        return "PAR"
    if score >= 30:
        return "BELOW"
    return "RISK"


def heat_band(score, evidence_count):
    if evidence_count <= 0 or score is None:
        return "NO_EVIDENCE"
    if score >= 75:
        return "ELITE_EDGE"
    if score >= 60:
        return "ABOVE_EXPECTED"
    if score >= 45:
        return "PAR"
    if score >= 30:
        return "BELOW_EXPECTED"
    return "RISK"


def colour_intent(band):
    return {
        "ELITE_EDGE": "cyan/green",
        "ABOVE_EXPECTED": "blue",
        "PAR": "muted",
        "BELOW_EXPECTED": "amber",
        "RISK": "orange/red",
        "NO_EVIDENCE": "grey",
    }.get(band, "grey")


def normalise_factor_score(value):
    n = to_float(value)
    if n is None:
        return None
    if n <= 10:
        return n * 10
    return max(0.0, min(100.0, n))


def choose_score(rows, factor_names, fallback_cols=()):
    for row in rows:
        factor = text(row.get("factor") or row.get("factor_label")).upper().replace(" ", "_")
        if factor in factor_names:
            n = normalise_factor_score(row.get("factor_score"))
            if n is not None:
                return n, f"factor:{factor}"
    for row in rows:
        for col in fallback_cols:
            if col in row:
                n = normalise_factor_score(row.get(col))
                if n is not None:
                    return n, col
    return None, ""


def index_single(rows):
    result = {}
    for row in rows:
        k = key(row)
        if k and k not in result:
            result[k] = row
    return result


def index_factor_rows(rows):
    result = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return result


def build():
    governed = read_csv(SOURCES["governed"])
    if not governed:
        raise SystemExit("Missing governed board input")

    factor_rows = index_factor_rows(read_csv(SOURCES["factor_lab"]) or read_csv(SOURCES["factor_scorecard"]))
    runner_enrichment = index_single(read_csv(SOURCES["runner_enrichment"]))
    connection = index_single(read_csv(SOURCES["connection"]))
    campaign = index_single(read_csv(SOURCES["campaign"]))
    command = index_single(read_csv(SOURCES["command"]))

    grouped = defaultdict(list)
    for row in governed:
        grouped[race_key(row)].append(row)

    expected_by_race = {}
    for rk, rows in grouped.items():
        target_values = []
        projected_values = []
        total_values = []
        for row in rows:
            for source_row in [row, runner_enrichment.get(key(row), {}), command.get(key(row), {})]:
                n = to_float(source_row.get("race_target_rating_v5_2"))
                if n is not None:
                    target_values.append(n)
                n = to_float(source_row.get("projected_rating_V6_1_RESEARCH") or source_row.get("projected_rating_v6_1_research"))
                if n is not None:
                    projected_values.append(n)
                n = to_float(source_row.get("total_rating_points"))
                if n is not None:
                    total_values.append(n)
        if target_values:
            expected_by_race[rk] = (statistics.median(target_values), "race_target_rating_v5_2")
        elif projected_values:
            expected_by_race[rk] = (statistics.median(projected_values), "median_projected_rating_V6_1_RESEARCH")
        elif total_values:
            expected_by_race[rk] = (statistics.median(total_values), "median_total_rating_points")
        else:
            expected_by_race[rk] = (None, "SOURCE_UNAVAILABLE")

    output = []
    for row in governed:
        k = key(row)
        rk = race_key(row)
        ren = runner_enrichment.get(k, {})
        conn = connection.get(k, {})
        camp = campaign.get(k, {})
        cmd = command.get(k, {})
        frows = factor_rows.get(k, [])
        source_pool = [row, ren, cmd]

        runner_rating = None
        runner_rating_source = ""
        for source_row in source_pool:
            runner_rating, runner_rating_source = first_num(source_row, [
                "projected_rating_V6_1_RESEARCH", "projected_rating_v6_1_research", "projected_rating_v5_2",
                "projected_rating", "rating_ladder_score", "total_rating_points", "edgeiq_score_overall_v3",
                "score_overall", "confidence_adjusted_rating_v6", "strength_adjusted_rating_v6",
            ])
            if runner_rating is not None:
                break

        expected_rating, expected_source = expected_by_race.get(rk, (None, "SOURCE_UNAVAILABLE"))
        rating_gap = runner_rating - expected_rating if runner_rating is not None and expected_rating is not None else None

        distance_score, distance_source = choose_score(frows + [ren, cmd], {"DISTANCE"}, ["score_distance", "edgeiq_score_distance_v3"])
        condition_score, condition_source = choose_score(frows + [ren, cmd], {"CONDITION"}, ["score_condition", "edgeiq_score_condition_v3"])
        class_score, class_source = choose_score(frows + [ren, cmd], {"CLASS"}, ["score_class", "edgeiq_score_class_v3"])
        campaign_score, campaign_source = choose_score(frows + [ren, cmd, camp], {"CAMPAIGN"}, ["score_campaign", "edgeiq_score_campaign_v3", "edgeiq_campaign_score_v1"])
        connection_score, connection_source = choose_score(frows + [ren, cmd, conn], {"CONNECTIONS", "CONNECTION"}, ["score_connections", "edgeiq_score_connections_v3", "connection_score"])

        components = []
        rating_component = None
        if rating_gap is not None:
            rating_component = max(0.0, min(100.0, 50.0 + rating_gap * 2.5))
            components.append(rating_component)
        for score in [distance_score, condition_score, class_score, campaign_score, connection_score]:
            if score is not None:
                components.append(score)
        overall = sum(components) / len(components) if components else None
        band = heat_band(overall, len(components))

        output.append({
            "race_date": race_date(row),
            "track": text(row.get("track")),
            "race_no": race_no(row),
            "race_key": text(row.get("race_key")) or rk,
            "runner_key": text(row.get("runner_key")),
            "horse": horse_name(row),
            "horse_key": text(row.get("horse_key")) or clean_horse(horse_name(row)),
            "runner_rating": fmt_num(runner_rating),
            "runner_rating_source": runner_rating_source,
            "expected_rating": fmt_num(expected_rating),
            "expected_rating_source": expected_source,
            "rating_gap": fmt_num(rating_gap),
            "distance_heat": heat_label(distance_score),
            "condition_heat": heat_label(condition_score),
            "class_heat": heat_label(class_score),
            "campaign_heat": heat_label(campaign_score),
            "connections_heat": heat_label(connection_score),
            "distance_score": fmt_num(distance_score),
            "condition_score": fmt_num(condition_score),
            "class_score": fmt_num(class_score),
            "campaign_score": fmt_num(campaign_score),
            "connections_score": fmt_num(connection_score),
            "overall_heat_score": fmt_num(overall),
            "heat_band": band,
            "heat_colour_intent": colour_intent(band),
            "evidence_status": "EVIDENCE_AVAILABLE" if components else "NO_EVIDENCE",
            "source_trace": ";".join(filter(None, [runner_rating_source, distance_source, condition_source, class_source, campaign_source, connection_source])),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(output)

    race_count = len({row["race_key"] for row in output})
    rows = len(output)
    expected_counts = Counter(row["expected_rating_source"] for row in output)
    band_counts = Counter(row["heat_band"] for row in output)
    evidence_rows = sum(1 for row in output if row["evidence_status"] == "EVIDENCE_AVAILABLE")
    summary_rows = [
        {"metric": "rows", "value": rows},
        {"metric": "races", "value": race_count},
        {"metric": "evidence_rows", "value": evidence_rows},
        {"metric": "evidence_coverage_pct", "value": f"{(evidence_rows / rows * 100 if rows else 0):.2f}"},
    ]
    for name, count in sorted(expected_counts.items()):
        summary_rows.append({"metric": f"expected_rating_source_{name}", "value": count})
    for name, count in sorted(band_counts.items()):
        summary_rows.append({"metric": f"heat_band_{name}", "value": count})

    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    REPORT.write_text(
        "EDGEIQ_RATINGS_INTELLIGENCE_HEATMAP_V1\n\n"
        f"Rows: {rows}\n"
        f"Races: {race_count}\n"
        f"Evidence rows: {evidence_rows}\n"
        f"Evidence coverage: {(evidence_rows / rows * 100 if rows else 0):.2f}%\n\n"
        "Expected race rating priority used: race_target_rating_v5_2, median projected_rating_V6_1_RESEARCH, median total_rating_points, then source unavailable.\n"
        "Per-runner heat uses current runner/race data and existing evidence score feeds only. Pricing, probabilities, V6.1 and V7.2G2 were not changed.\n",
        encoding="utf-8",
    )
    print(f"Built {OUT}")
    print(f"rows={rows} races={race_count} evidence_rows={evidence_rows}")


if __name__ == "__main__":
    build()
