from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, coverage_pct, has_value, read_csv, write_csv


MASTER = DATA / "edgeiq_results_master_v1.csv"


def main() -> None:
    rows = list(read_csv(MASTER))
    years: dict[str, dict[str, object]] = {}
    months: dict[tuple[str, str], dict[str, object]] = {}
    meetings: dict[str, dict[str, object]] = {}
    races: dict[str, dict[str, object]] = {}

    race_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    meeting_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    year_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    month_rows: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        race_rows[row["race_key"]].append(row)
        meeting_rows[row["meeting_key"]].append(row)
        year_rows[row["year"]].append(row)
        month_rows[(row["year"], row["month"])].append(row)

    for year, group in year_rows.items():
        dates = [row["race_date"] for row in group if row["race_date"]]
        years[year] = {
            "year": year,
            "meetings": len({row["meeting_key"] for row in group}),
            "races": len({row["race_key"] for row in group}),
            "runner_rows": len(group),
            "tracks": len({row["normalized_track"] for row in group}),
            "first_date": min(dates) if dates else "",
            "last_date": max(dates) if dates else "",
        }

    for (year, month), group in month_rows.items():
        dates = [row["race_date"] for row in group if row["race_date"]]
        months[(year, month)] = {
            "year": year,
            "month": month,
            "month_name": group[0]["month_name"],
            "meetings": len({row["meeting_key"] for row in group}),
            "races": len({row["race_key"] for row in group}),
            "runner_rows": len(group),
            "tracks": len({row["normalized_track"] for row in group}),
            "first_date": min(dates) if dates else "",
            "last_date": max(dates) if dates else "",
        }

    for meeting_key, group in meeting_rows.items():
        first = group[0]
        meetings[meeting_key] = {
            "race_date": first["race_date"],
            "year": first["year"],
            "month": first["month"],
            "track": first["track"],
            "normalized_track": first["normalized_track"],
            "meeting_key": meeting_key,
            "races": len({row["race_key"] for row in group}),
            "runner_rows": len(group),
            "first_race_time": "",
            "last_race_time": "",
            "condition": first["condition"],
            "rail": first["rail"],
            "result_status": "RESULTED" if any(row["result_status"] == "RESULTED" for row in group) else first["result_status"],
        }

    for race_key, group in race_rows.items():
        first = group[0]
        total = len(group)
        sp = sum(1 for row in group if has_value(row["sp"]) or has_value(row["starting_price"]))
        margin = sum(1 for row in group if has_value(row["margin"]) or has_value(row["beaten_margin"]))
        epi = sum(1 for row in group if has_value(row["epi_post"]))
        sectional = sum(1 for row in group if row["sectional_status"] == "CAPTURED")
        races[race_key] = {
            "race_date": first["race_date"],
            "year": first["year"],
            "month": first["month"],
            "track": first["track"],
            "normalized_track": first["normalized_track"],
            "meeting_key": first["meeting_key"],
            "race_no": first["race_no"],
            "race_key": race_key,
            "race_name": first["race_name"],
            "distance": first["distance"],
            "class": first["class"],
            "condition": first["condition"],
            "field_size": total,
            "result_status": "RESULTED" if any(row["result_status"] == "RESULTED" for row in group) else first["result_status"],
            "sp_coverage_pct": coverage_pct(sp, total),
            "margin_coverage_pct": coverage_pct(margin, total),
            "epi_coverage_pct": coverage_pct(epi, total),
            "sectional_coverage_pct": coverage_pct(sectional, total),
        }

    write_csv(DATA / "edgeiq_results_calendar_years_v1.csv", sorted(years.values(), key=lambda r: r["year"]), ["year", "meetings", "races", "runner_rows", "tracks", "first_date", "last_date"])
    write_csv(DATA / "edgeiq_results_calendar_months_v1.csv", sorted(months.values(), key=lambda r: (r["year"], r["month"])), ["year", "month", "month_name", "meetings", "races", "runner_rows", "tracks", "first_date", "last_date"])
    write_csv(DATA / "edgeiq_results_calendar_meetings_v1.csv", sorted(meetings.values(), key=lambda r: (r["race_date"], r["normalized_track"])), ["race_date", "year", "month", "track", "normalized_track", "meeting_key", "races", "runner_rows", "first_race_time", "last_race_time", "condition", "rail", "result_status"])
    write_csv(DATA / "edgeiq_results_calendar_races_v1.csv", sorted(races.values(), key=lambda r: (r["race_date"], r["normalized_track"], int(r["race_no"]) if str(r["race_no"]).isdigit() else 999)), ["race_date", "year", "month", "track", "normalized_track", "meeting_key", "race_no", "race_key", "race_name", "distance", "class", "condition", "field_size", "result_status", "sp_coverage_pct", "margin_coverage_pct", "epi_coverage_pct", "sectional_coverage_pct"])
    summary = [{"years": len(years), "months": len(months), "meetings": len(meetings), "races": len(races), "runner_rows": len(rows)}]
    write_csv(DATA / "edgeiq_results_calendar_summary_v1.csv", summary, list(summary[0].keys()))
    print(f"Wrote calendar index for {len(races)} races")


if __name__ == "__main__":
    main()
