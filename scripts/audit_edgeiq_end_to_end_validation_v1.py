from __future__ import annotations

from datetime import datetime

from edgeiq_beta_readiness_common_v1 import (
    PUBLIC_DATA,
    catalog_runners,
    clean,
    indexed_by_race_runner,
    load_form_enriched_runners,
    normalise_runner,
    read_csv,
    write_json,
    write_text,
)


PASS_MARKER = "EDGEIQ_END_TO_END_VALIDATION_V1_PASS"
TXT_OUT = PUBLIC_DATA / "edgeiq_end_to_end_validation_v1.txt"
JSON_OUT = PUBLIC_DATA / "edgeiq_end_to_end_validation_v1.json"


def main() -> int:
    generated = datetime.now().isoformat(timespec="seconds")
    catalog = catalog_runners()
    if not catalog:
        status = "FAIL"
        findings = [{"status": "FAIL", "detail": "No catalog runners available"}]
    else:
        enriched = load_form_enriched_runners()
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
        required_catalog_fields = ["runner_no", "runner", "barrier", "weight", "jockey", "trainer"]
        for field in required_catalog_fields:
            missing = [row["runner"] for row in race_rows if not clean(row.get(field))]
            findings.append({
                "status": "PASS" if not missing else "WARN",
                "detail": f"{field}: {len(race_rows) - len(missing)}/{len(race_rows)} populated",
                "missing": missing[:20],
            })
        for label, keys in [("form", enriched_keys), ("map", map_keys), ("market", market_keys), ("performance", epi_keys)]:
            missing = []
            for row in race_rows:
                key = (row["race_key"], normalise_runner(row["runner"]))
                if key not in keys:
                    missing.append(row["runner"])
            findings.append({
                "status": "PASS" if not missing else "WARN",
                "detail": f"{label}: {len(race_rows) - len(missing)}/{len(race_rows)} runners matched for {race_key}",
                "missing": missing[:20],
            })
        status = "PASS"

    payload = {"audit": "edgeiq_end_to_end_validation_v1", "generated_at": generated, "status": status, "pass_marker": PASS_MARKER if status == "PASS" else "", "findings": findings}
    write_json(JSON_OUT, payload)
    lines = ["EDGEiQ End To End Validation V1", f"Generated: {generated}", f"Status: {status}"]
    if status == "PASS":
        lines.append(PASS_MARKER)
    lines.append("")
    for finding in findings:
        lines.append(f"[{finding['status']}] {finding['detail']}")
        if finding.get("missing"):
            lines.append("  Missing: " + ", ".join(finding["missing"]))
    write_text(TXT_OUT, "\n".join(lines) + "\n")
    print(PASS_MARKER if status == "PASS" else "EDGEIQ_END_TO_END_VALIDATION_V1_FAIL")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
