from __future__ import annotations

from edgeiq_results_common_v1 import DATA, first, has_value, now_iso, read_csv, write_csv


OUT = DATA / "edgeiq_column_population_v1.csv"

COLUMNS = {
    "NO": ["saddlecloth", "horse_no", "runner_no", "runner_number"],
    "SILK": ["silkUrl", "silk_url", "local_silk_path"],
    "RUNNER": ["horse", "runner", "runner_name"],
    "BAR": ["barrier", "draw"],
    "JOCKEY": ["jockey", "rider"],
    "TRAINER": ["trainer"],
    "LIVE": ["live_price", "market_price", "fixed_win", "ui_price"],
    "FLUC": ["flucs", "last10", "last_10", "open_price", "mid_price"],
    "FAIR": ["fair_price", "rated_price", "ui_fair_price", "V6_1_RESEARCH_fair_price"],
    "EDGE": ["edge_pct", "ui_edge_pct"],
    "SP": ["sp", "starting_price"],
    "GEAR": ["gear_current", "gear_changes", "gear_added", "gear_removed", "first_time_gear"],
    "RESULT": ["position", "result_status"],
    "EPI": ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "epi_post", "runner_rating"],
    "SECTIONALS": ["split_lengths", "sectional_600", "std_600_len", "sectional_status"],
}

FEEDS = {
    "runner_board": "edgeiq_live_runner_board_governed_v1.csv",
    "meeting_universe": "edgeiq_vic_three_day_meeting_universe.csv",
    "results_master": "edgeiq_results_master_v1.csv",
    "form_sectional_terminal": "edgeiq_form_sectional_terminal_feed_v1.csv",
    "gear_terminal": "edgeiq_gear_terminal_feed_v1.csv",
}

FEED_COLUMN_SCOPE = {
    "runner_board": ["NO", "SILK", "RUNNER", "BAR", "JOCKEY", "TRAINER", "LIVE", "FLUC", "FAIR", "EDGE", "EPI"],
    "meeting_universe": ["NO", "SILK", "RUNNER", "BAR", "JOCKEY", "TRAINER", "LIVE", "FLUC", "FAIR", "EDGE"],
    "results_master": ["NO", "SILK", "RUNNER", "BAR", "JOCKEY", "TRAINER", "SP", "RESULT", "EPI", "SECTIONALS"],
    "form_sectional_terminal": ["RUNNER", "SP", "RESULT", "EPI", "SECTIONALS"],
    "gear_terminal": ["RUNNER", "GEAR"],
}


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def main() -> None:
    output = []
    for feed_label, filename in FEEDS.items():
        rows = load(filename)
        for column, keys in COLUMNS.items():
            if column not in FEED_COLUMN_SCOPE.get(feed_label, []):
                output.append({
                    "feed": feed_label,
                    "file": filename,
                    "column": column,
                    "keys_checked": "|".join(keys),
                    "rows": len(rows),
                    "populated": "",
                    "missing": "",
                    "population_pct": "",
                    "status": "N/A",
                    "built_at": now_iso(),
                })
                continue
            populated = sum(1 for row in rows if has_value(first(row, keys)))
            total = len(rows)
            pct = round((populated / total) * 100, 2) if total else 0
            output.append({
                "feed": feed_label,
                "file": filename,
                "column": column,
                "keys_checked": "|".join(keys),
                "rows": total,
                "populated": populated,
                "missing": total - populated,
                "population_pct": pct,
                "status": "OK" if pct >= 99 or total == 0 else "FIX_REQUIRED",
                "built_at": now_iso(),
            })
    fields = ["feed", "file", "column", "keys_checked", "rows", "populated", "missing", "population_pct", "status", "built_at"]
    write_csv(OUT, output, fields)
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
