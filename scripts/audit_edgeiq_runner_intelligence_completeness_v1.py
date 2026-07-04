from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, has_value, normalized_runner, now_iso, read_csv, write_csv


OUT = DATA / "edgeiq_runner_intelligence_completeness_v1.csv"


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def runner_key(row: dict[str, str]) -> str:
    runner = normalized_runner(first(row, ["horse", "runner", "runner_name", "normalized_runner"]))
    return runner or first(row, ["runner_key"])


def by_runner(rows: list[dict[str, str]], keys: list[str]) -> set[str]:
    out = set()
    for row in rows:
        key = runner_key(row)
        if not key:
            continue
        if any(has_value(first(row, [field])) for field in keys):
            out.add(key)
    return out


def main() -> None:
    board = load("edgeiq_live_runner_board_governed_v1.csv")
    total = len(board)
    universe = {runner_key(row) for row in board if runner_key(row)}
    feeds = {
        "DNA": by_runner(load("edgeiq_runner_dna_drawer_feed_v2.csv"), ["dna_score", "runner_dna", "profile_summary", "runner_key"]),
        "Explainability": by_runner(load("edgeiq_explainability_terminal_feed_v1_2.csv"), ["explainability_summary", "factor_summary", "runner_key"]),
        "Profiles": by_runner(load("edgeiq_runners_enrichment_feed_v1_1.csv"), ["profile_summary", "runner_profile", "runner_key"]),
        "Distance": by_runner(board, ["distance", "race_distance"]),
        "Condition": by_runner(board, ["track_condition", "condition", "going"]),
        "Class": by_runner(board, ["race_class", "class"]),
        "Sectionals": by_runner(load("edgeiq_form_sectional_terminal_feed_v1.csv"), ["split_lengths", "finish_len", "sectional_status"]),
        "Speed": by_runner(board, ["speed_map_bucket", "run_style", "map_x_pct", "early_speed_rating"]),
        "Connections": by_runner(board, ["jockey", "trainer"]),
    }
    output = []
    for area, keys in feeds.items():
        matched = len(universe & keys)
        pct = round((matched / total) * 100, 2) if total else 0
        output.append(
            {
                "area": area,
                "runner_rows": total,
                "populated_rows": matched,
                "missing_rows": max(0, total - matched),
                "coverage_pct": pct,
                "status": "OK" if pct >= 95 else "EXPLAIN",
                "explanation": "" if pct >= 95 else "Coverage depends on current sidecar source availability; frontend falls back where possible.",
                "built_at": now_iso(),
            }
        )
    fields = ["area", "runner_rows", "populated_rows", "missing_rows", "coverage_pct", "status", "explanation", "built_at"]
    write_csv(OUT, output, fields)
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
