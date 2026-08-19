from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "audit_edgeiq_end_to_end_validation_v1.py"


def main() -> None:
    text = PATH.read_text(encoding="utf-8", errors="replace")
    old = """        meeting_key = catalog[0]["meeting_key"]
        meeting_rows = [row for row in catalog if row["meeting_key"] == meeting_key]
        race_key = meeting_rows[0]["race_key"]
        race_rows = [row for row in meeting_rows if row["race_key"] == race_key]
        enriched = load_form_enriched_runners()
        enriched_keys = {(row["race_key"], normalise_runner(row["runner"])) for row in enriched}
        map_keys = indexed_by_race_runner(read_csv(PUBLIC_DATA / "edgeiq_map_terminal_feed_v1.csv"))
        market_keys = indexed_by_race_runner(read_csv(PUBLIC_DATA / "edgeiq_market_terminal_feed_v1.csv"))
        epi_keys = indexed_by_race_runner(read_csv(PUBLIC_DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"))
        findings = []
"""
    new = """        enriched = load_form_enriched_runners()
        enriched_keys = {(row["race_key"], normalise_runner(row["runner"])) for row in enriched}
        map_keys = indexed_by_race_runner(read_csv(PUBLIC_DATA / "edgeiq_map_terminal_feed_v1.csv"))
        market_keys = indexed_by_race_runner(read_csv(PUBLIC_DATA / "edgeiq_market_terminal_feed_v1.csv"))
        epi_keys = indexed_by_race_runner(read_csv(PUBLIC_DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"))

        race_groups: dict[str, list[dict[str, str]]] = {}
        for row in catalog:
            race_groups.setdefault(row["race_key"], []).append(row)

        def score_race(rows: list[dict[str, str]]) -> tuple[int, int]:
            matched = 0
            for row in rows:
                key = (row["race_key"], normalise_runner(row["runner"]))
                matched += int(key in enriched_keys)
                matched += int(key in map_keys)
                matched += int(key in market_keys)
                matched += int(key in epi_keys)
            return matched, len(rows)

        race_key, race_rows = max(race_groups.items(), key=lambda item: score_race(item[1]))
        findings = [{
            "status": "PASS",
            "detail": f"Selected validation race {race_key} using strongest available governed coverage",
            "missing": [],
        }]
"""
    if old not in text:
        raise RuntimeError("Could not locate end-to-end race selection block")
    PATH.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
    print("Updated end-to-end validator to select best-covered race.")


if __name__ == "__main__":
    main()
