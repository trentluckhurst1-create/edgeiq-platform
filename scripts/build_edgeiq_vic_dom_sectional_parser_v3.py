from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()

RAW = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_vic_dom_sectionals_raw_body_v1.txt"

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_vic_dom_sectionals_v3.csv"

text = RAW.read_text(encoding="utf-8", errors="ignore")

lines = [x.strip() for x in text.splitlines()]
lines = [x for x in lines if x]

print("=" * 80)
print("TOTAL LINES:", len(lines))
print("=" * 80)

horses = []

for idx, line in enumerate(lines):

    pos_match = re.match(r'^(\d+)(?:st|nd|rd|th)$', line)

    if pos_match and idx + 1 < len(lines):

        horse_line = lines[idx + 1]

        horse_match = re.match(r'^\d+\.\s(.+?)\s\(\d+\)$', horse_line)

        if horse_match:

            horses.append({
                "position": pos_match.group(1),
                "horse": horse_match.group(1).strip()
            })

metrics = []

i = 0

while i < len(lines):

    line = lines[i]

    if re.match(r'^\d+(?:\(\+?-?\d+\))?$', line):

        try:

            distance = re.search(r'(\d+)', line).group(1)

            early = re.search(r'([\d\.]+)', lines[i + 2]).group(1)
            mid   = re.search(r'([\d\.]+)', lines[i + 4]).group(1)
            late  = re.search(r'([\d\.]+)', lines[i + 6]).group(1)
            peak  = re.search(r'([\d\.]+)', lines[i + 8]).group(1)
            avg   = re.search(r'([\d\.]+)', lines[i + 10]).group(1)

            metrics.append({
                "distance_ran_m": distance,
                "early_speed_kmh": early,
                "mid_speed_kmh": mid,
                "late_speed_kmh": late,
                "peak_speed_kmh": peak,
                "avg_speed_kmh": avg
            })

            print("METRIC BLOCK FOUND:", distance, early, mid, late, peak, avg)

            i += 11

            continue

        except Exception as e:

            print("PARSE FAIL:", repr(e))

    i += 1

rows = []

for idx in range(min(len(horses), len(metrics))):

    row = {
        **horses[idx],
        **metrics[idx]
    }

    row["horse_key"] = re.sub(r'[^A-Z0-9]', '', row["horse"].upper())

    row["source"] = "RACINGCOM_DOM_IFRAME_V3"

    rows.append(row)

df = pd.DataFrame(rows)

df.to_csv(OUT, index=False)

print("=" * 80)
print("HORSES FOUND:", len(horses))
print("METRICS FOUND:", len(metrics))
print("FINAL ROWS:", len(df))
print("=" * 80)

if len(df):

    print(df.to_string(index=False))

print("=" * 80)
print("SAVED:", OUT)
