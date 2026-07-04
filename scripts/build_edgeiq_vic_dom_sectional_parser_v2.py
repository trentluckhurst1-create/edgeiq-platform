from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()

RAW = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_vic_dom_sectionals_raw_body_v1.txt"

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_vic_dom_sectionals_v2.csv"

text = RAW.read_text(encoding="utf-8", errors="ignore")

lines = [x.strip() for x in text.splitlines()]
lines = [x for x in lines if x]

horses = []

i = 0

while i < len(lines):

    line = lines[i]

    horse_match = re.match(r'^(\d+)(?:st|nd|rd|th)$', line)

    if horse_match and i + 1 < len(lines):

        horse_line = lines[i + 1]

        horse_name_match = re.match(r'^\d+\.\s(.+?)\s\(\d+\)$', horse_line)

        if horse_name_match:

            horse = horse_name_match.group(1).strip()

            horses.append({
                "horse": horse,
                "position": horse_match.group(1)
            })

    i += 1

metrics = []

for idx, line in enumerate(lines):

    if "metres" in line:

        try:

            distance = re.search(r'(\d+)', line).group(1)

            early = re.search(r'([\d\.]+)', lines[idx + 2]).group(1)
            mid   = re.search(r'([\d\.]+)', lines[idx + 4]).group(1)
            late  = re.search(r'([\d\.]+)', lines[idx + 6]).group(1)
            peak  = re.search(r'([\d\.]+)', lines[idx + 8]).group(1)
            avg   = re.search(r'([\d\.]+)', lines[idx + 10]).group(1)

            metrics.append({
                "distance_ran_m": distance,
                "early_speed_kmh": early,
                "mid_speed_kmh": mid,
                "late_speed_kmh": late,
                "peak_speed_kmh": peak,
                "avg_speed_kmh": avg
            })

        except:
            pass

rows = []

for idx in range(min(len(horses), len(metrics))):

    row = {
        **horses[idx],
        **metrics[idx]
    }

    row["horse_key"] = re.sub(r'[^A-Z0-9]', '', row["horse"].upper())

    row["source"] = "RACINGCOM_DOM_IFRAME_V2"

    rows.append(row)

df = pd.DataFrame(rows)

df.to_csv(OUT, index=False)

print("=" * 100)
print("EDGEIQ VIC DOM SECTIONAL PARSER V2")
print("=" * 100)
print("HORSES:", len(horses))
print("METRICS:", len(metrics))
print("FINAL ROWS:", len(df))
print("=" * 100)

if len(df):
    print(df.to_string(index=False))

print("=" * 100)
print("SAVED:", OUT)
