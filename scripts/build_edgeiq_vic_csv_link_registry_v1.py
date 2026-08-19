from pathlib import Path
import pandas as pd
import re
from urllib.parse import urljoin

ROOT = Path.cwd()

RAW_DIR = ROOT / "outputs" / "racingcom_html"
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUT_DIR = ROOT / "outputs" / "racingcom_csv_links"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

OUT = PUBLIC / "edgeiq_vic_csv_link_registry_v1.csv"
DIAG = PUBLIC / "edgeiq_vic_csv_link_registry_diagnostics_v1.csv"

csv_pattern = re.compile(
    r'https?:\/\/[^"]+?\.csv(?:\?[^"]+)?',
    re.IGNORECASE
)

relative_pattern = re.compile(
    r'["'']([^"'']+?\.csv(?:\?[^"'']+)?)["'']',
    re.IGNORECASE
)

rows = []

for path in RAW_DIR.glob("*.html"):

    text = path.read_text(encoding="utf-8", errors="ignore")

    absolute = csv_pattern.findall(text)

    relative = []
    for m in relative_pattern.findall(text):
        if ".csv" in m.lower():
            relative.append(m)

    all_links = set()

    for link in absolute:
        all_links.add(link)

    for link in relative:
        if link.startswith("http"):
            all_links.add(link)
        else:
            all_links.add(urljoin("https://www.racing.com", link))

    for link in sorted(all_links):

        lower = link.lower()

        rows.append({
            "source_file": path.name,
            "csv_url": link,
            "is_sectional": any(x in lower for x in [
                "sectional",
                "split",
                "stride",
                "sectionals",
            ]),
            "is_race_data": any(x in lower for x in [
                "race",
                "meeting",
                "results",
            ]),
            "state_focus": "VIC",
        })

out = pd.DataFrame(rows)

if len(out):
    out = out.drop_duplicates("csv_url")

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "html_files_scanned": len(list(RAW_DIR.glob("*.html"))),
    "csv_links_discovered": len(out),
    "sectional_links": int(out["is_sectional"].sum()) if len(out) else 0,
    "race_data_links": int(out["is_race_data"].sum()) if len(out) else 0,
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ VIC CSV LINK REGISTRY V1")
print("=" * 100)

print(diag.to_string(index=False))

print()

if len(out):
    print(out.head(50).to_string(index=False))

print()
print("SAVED:", OUT)
print("SAVED:", DIAG)
