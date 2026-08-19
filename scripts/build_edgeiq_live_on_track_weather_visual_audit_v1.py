import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/edgeiq_on_track_weather_governed_v1_2.json"
OUT_DIR = ROOT / "public/data/visual_audits/edgeiq_live_on_track_weather_v1"
OUT = OUT_DIR / "live_on_track_weather_audit.svg"


def line(x: int, y: int, label: str, value: object) -> str:
    safe_label = html.escape(str(label))
    safe_value = html.escape("-" if value is None else str(value))
    return (
        f'<text x="{x}" y="{y}" class="label">{safe_label}</text>'
        f'<text x="{x + 118}" y="{y}" class="value">{safe_value}</text>'
    )


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    cards = []
    for idx, record in enumerate(records):
        x = 28 + idx * 334
        y = 96
        parts = [
            f'<rect x="{x}" y="{y}" width="310" height="438" rx="16" class="card"/>',
            f'<text x="{x + 18}" y="{y + 34}" class="track">{html.escape(str(record.get("track_group", "-")))}</text>',
            f'<text x="{x + 18}" y="{y + 70}" class="state">{html.escape(str(record.get("governed_source_state", "-")))}</text>',
            f'<text x="{x + 18}" y="{y + 96}" class="fresh">{html.escape(str(record.get("freshness_status", "-")))} · {html.escape(str(record.get("source_type", "-")))}</text>',
        ]
        yy = y + 132
        for label, value in [
            ("Observed", record.get("observation_local")),
            ("Source time", record.get("source_timestamp")),
            ("Temp", f'{record.get("temperature_c", "-")} C'),
            ("Humidity", f'{record.get("humidity_percent", "-")}%'),
            ("Wind", f'{record.get("wind_speed_kmh", "-")} km/h {record.get("wind_direction_text", "")}'),
            ("Gust", f'{record.get("wind_gust_kmh", "-")} km/h'),
            ("Rain 24h", f'{record.get("rain_24h_mm", "-")} mm'),
            ("Track", record.get("going_report") or record.get("weather_comment") or "-"),
        ]:
            parts.append(line(x + 18, yy, label, value))
            yy += 32
        parts.append(f'<text x="{x + 18}" y="{y + 408}" class="endpoint">{html.escape(str(record.get("live_request_url", "-")))}</text>')
        cards.append("\n".join(parts))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="680" viewBox="0 0 1400 680">
  <defs>
    <radialGradient id="glow" cx="50%" cy="0%" r="70%">
      <stop offset="0%" stop-color="#0a3033"/>
      <stop offset="100%" stop-color="#020508"/>
    </radialGradient>
    <style>
      .title{{font:700 28px Arial,sans-serif;fill:#f2fbfb}}
      .sub{{font:500 14px Arial,sans-serif;fill:#8ca8ac}}
      .card{{fill:rgba(3,8,10,.82);stroke:rgba(90,255,220,.22);stroke-width:1}}
      .track{{font:800 13px Arial,sans-serif;fill:#33808A;letter-spacing:2px}}
      .state{{font:700 23px Arial,sans-serif;fill:#f4fbfb}}
      .fresh{{font:700 14px Arial,sans-serif;fill:#7fd7ce}}
      .label{{font:800 10px Arial,sans-serif;fill:#6f878b;letter-spacing:1px;text-transform:uppercase}}
      .value{{font:500 13px Arial,sans-serif;fill:#dcebed}}
      .endpoint{{font:500 10px Arial,sans-serif;fill:#86a3a7}}
      .footer{{font:500 12px Arial,sans-serif;fill:#819396}}
    </style>
  </defs>
  <rect width="1400" height="680" fill="url(#glow)"/>
  <text x="28" y="42" class="title">EDGEiQ Live On-Track Weather Audit</text>
  <text x="28" y="66" class="sub">Generated from public/data/edgeiq_on_track_weather_governed_v1_2.json · {html.escape(str(payload.get("generated_at", "-")))} · {len(records)} approved live records</text>
  {"".join(cards)}
  <text x="28" y="612" class="footer">No values fabricated. This static audit renders the governed terminal feed produced by the ingestion pipeline.</text>
</svg>'''
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"EDGEIQ_LIVE_ON_TRACK_WEATHER_VISUAL_AUDIT_V1_BUILT {OUT}")


if __name__ == "__main__":
    main()
