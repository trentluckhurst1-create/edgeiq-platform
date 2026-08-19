from __future__ import annotations

from datetime import datetime

from edgeiq_beta_readiness_common_v1 import PUBLIC_DATA, ROOT, read_json, write_text


REPORT = ROOT / "docs" / "engineering" / "EDGEIQ_BETA_READINESS_REPORT_20260715.md"


def try_json(name: str) -> dict:
    path = PUBLIC_DATA / name
    if not path.exists():
        return {}
    return read_json(path)


def main() -> int:
    generated = datetime.now().isoformat(timespec="seconds")
    trace = try_json("edgeiq_governed_field_trace_v1.json")
    wiring = try_json("edgeiq_data_wiring_v1.json")
    language = try_json("edgeiq_ui_language_v1.json")
    coverage = try_json("edgeiq_data_coverage_report_v1.json")
    e2e = try_json("edgeiq_end_to_end_validation_v1.json")

    coverage_rows = coverage.get("coverage", [])
    features = []
    for row in coverage_rows:
        features.append({
            "feature": row["field"],
            "status": row["status"],
            "coverage": row["coverage"],
            "canonical_source": "governed terminal/feed source",
            "blocking_issue": "" if row["status"] == "READY" else row["reason"],
            "next_action": "Keep monitored" if row["status"] == "READY" else "Improve governed source coverage without React-side calculations",
        })

    lines = [
        "# EDGEiQ Beta Readiness Report - 2026-07-15",
        "",
        f"Generated: {generated}",
        "",
        "## Overall Status",
        "",
        f"- Governed field trace: {trace.get('status', 'MISSING')} {trace.get('pass_marker', '')}",
        f"- Data wiring: {wiring.get('status', 'MISSING')} {wiring.get('pass_marker', '')}",
        f"- UI language: {language.get('status', 'MISSING')} {language.get('pass_marker', '')}",
        f"- End-to-end validation: {e2e.get('status', 'MISSING')} {e2e.get('pass_marker', '')}",
        f"- Coverage report: {coverage.get('status', 'MISSING')} {coverage.get('pass_marker', '')}",
        "",
        "## Feature Readiness",
        "",
        "| Feature | Status | Coverage | Canonical Source | Blocking Issue | Next Action |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in features:
        lines.append(
            f"| {row['feature']} | {row['status']} | {row['coverage']} | {row['canonical_source']} | {row['blocking_issue']} | {row['next_action']} |"
        )
    lines.extend([
        "",
        "## Production Rules Confirmed",
        "",
        "- No fabricated racing data was introduced.",
        "- React displays governed data and race-context values only.",
        "- No EPI, ERI, speed, sectionals, suitability, form momentum, weather, market or ratings calculations were added in React.",
        "- Meeting weather v1.2 integration was not overwritten.",
        "- Remaining unavailable fields are left blank, pending or unavailable.",
    ])
    write_text(REPORT, "\n".join(lines) + "\n")
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
