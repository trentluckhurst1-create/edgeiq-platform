from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
OUT_TXT = PUBLIC / "edgeiq_live_on_track_weather_ingestion_v1_final_report.txt"
OUT_JSON = PUBLIC / "edgeiq_live_on_track_weather_ingestion_v1_final_report.json"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    trace = load(PUBLIC / "edgeiq_turftrax_live_request_trace_v1.json")
    probe = load(PUBLIC / "edgeiq_live_on_track_weather_probe_v1.json")
    governed = load(PUBLIC / "edgeiq_on_track_weather_governed_v1_2.json")
    governed_audit = load(PUBLIC / "edgeiq_on_track_weather_governed_v1_2_audit.json")
    trace_by_track = {row.get("track_group"): row for row in trace.get("records", [])}
    probe_by_track = {row.get("track_group"): row for row in probe.get("records", [])}
    governed_by_track = {row.get("track_group"): row for row in governed.get("records", [])}
    tracks = ["Flemington", "Caulfield", "Sandown", "Mornington"]
    source_reports = []
    for track in tracks:
        c = trace_by_track.get(track, {})
        p = probe_by_track.get(track, {})
        g = governed_by_track.get(track, {})
        source_reports.append({
            "track_group": track,
            "request_contract": c.get("verification_status", "MISSING"),
            "endpoint": c.get("request_url", ""),
            "method": c.get("method", ""),
            "accessibility": p.get("accessibility", "MISSING"),
            "live_response_status": p.get("http_status", ""),
            "schema_status": p.get("schema_status", ""),
            "update_cadence": c.get("polling_interval_seconds", ""),
            "freshness": g.get("freshness_status", ""),
            "fields_supplied": [key for key in [
                "temperature_c", "humidity_percent", "wind_speed_kmh", "wind_direction_text",
                "wind_gust_kmh", "rain_today_mm", "rain_24h_mm", "rain_7d_mm", "weather_comment", "going_report",
            ] if g.get(key) not in (None, "", [])],
            "integration_status": g.get("governed_source_state", "MISSING"),
            "blocker": "" if p.get("accessibility") == "LIVE_RESPONSE_OK" else p.get("error", p.get("accessibility", "")),
        })
    pass_status = (
        trace.get("audit_status") == "EDGEIQ_LIVE_REQUEST_CONTRACT_TRACE_V1_PASS"
        and probe.get("audit_status") == "EDGEIQ_LIVE_ON_TRACK_WEATHER_PROBE_V1_PASS"
        and governed_audit.get("status") == "EDGEIQ_ON_TRACK_WEATHER_GOVERNED_V1_2_AUDIT_PASS"
        and all(report["request_contract"] == "PROVEN_FROM_CLIENT_CODE" for report in source_reports)
        and all(report["accessibility"] == "LIVE_RESPONSE_OK" for report in source_reports)
    )
    payload = {
        "status": "EDGEIQ_LIVE_ON_TRACK_WEATHER_INGESTION_V1_AUDIT_PASS" if pass_status else "EDGEIQ_LIVE_ON_TRACK_WEATHER_INGESTION_V1_AUDIT_WARN",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_reports": source_reports,
        "outputs": {
            "trace": "public/data/edgeiq_turftrax_live_request_trace_v1.json",
            "probe": "public/data/edgeiq_live_on_track_weather_probe_v1.json",
            "snapshot": "data/weather/live_raw_on_track_weather_v1.json",
            "governed": "public/data/edgeiq_on_track_weather_governed_v1_2.json",
        },
        "remaining_weather_gaps": [
            "BOM forecast and country-track fallback mapping remain separate follow-up work.",
            "Frontend should continue to label stale/aging/unavailable source states explicitly.",
        ],
        "next_actions": [
            "Build BOM forecast mapping for non-metropolitan tracks using official BOM location IDs.",
            "Create country-track fallback registry only after official on-track source discovery is exhausted.",
        ],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [payload["status"], f"generated_at={payload['generated_at']}", ""]
    for report in source_reports:
        lines.extend([
            f"{report['track_group']}",
            f"  endpoint={report['endpoint']}",
            f"  method={report['method']}",
            f"  contract={report['request_contract']}",
            f"  accessibility={report['accessibility']} status={report['live_response_status']} schema={report['schema_status']}",
            f"  freshness={report['freshness']} integration={report['integration_status']}",
            f"  fields={','.join(report['fields_supplied'])}",
            f"  blocker={report['blocker']}",
            "",
        ])
    lines.extend([
        "Remaining gaps:",
        *[f"- {item}" for item in payload["remaining_weather_gaps"]],
        "",
        "Next actions:",
        *[f"- {item}" for item in payload["next_actions"]],
    ])
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(payload["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
