from pathlib import Path
import pandas as pd
import re
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPOSITORY_ROOT / "docs" / "architecture" / "step202"

EXPECTED = "STEP201_REPOSITORY_CENSUS_V1_2.csv"
matches = list(REPOSITORY_ROOT.rglob(EXPECTED))

if len(matches) != 1:
    print("ERROR: STEP201 census not found.")
    sys.exit(1)

CENSUS = matches[0]
RAW_GRAPH = OUTPUT_DIR / "STEP202_DEPENDENCY_GRAPH_RAW.csv"

print("=" * 80)
print("STEP202E - PYTHON MODULE RESOLUTION")
print("=" * 80)
print()

census = pd.read_csv(CENSUS)
raw = pd.read_csv(RAW_GRAPH)

module_lookup = {}
path_lookup = {}

for _, row in census.iterrows():

    repo_path = str(row["repository_path"]).replace("\\", "/")
    asset_id = row["asset_id"]

    path_lookup[repo_path.lower()] = asset_id

    p = Path(repo_path)

    if p.suffix == ".py":

        module = ".".join(p.with_suffix("").parts)

        module_lookup[module.lower()] = asset_id

resolved = []
resolved_count = 0

for _, edge in raw.iterrows():

    relationship = str(edge["relationship"])
    target = str(edge["target"]).strip()

    asset = None

    if relationship in ("IMPORT","FROM_IMPORT"):

        target_module = target.split(",")[0].strip().lower()

        asset = module_lookup.get(target_module)

    if asset is None:

        target_lower = target.replace("\\","/").lower()

        for repo_path, asset_id in path_lookup.items():

            if repo_path in target_lower:

                asset = asset_id
                break

    if asset is None:
        continue

    resolved.append({
        "from_asset": edge["from_asset"],
        "to_asset": asset,
        "relationship": relationship,
        "evidence": target,
        "line": edge["line"]
    })

    resolved_count += 1

resolved_df = pd.DataFrame(resolved)

OUTPUT = OUTPUT_DIR / "STEP202_DEPENDENCY_GRAPH_V2.csv"

resolved_df.to_csv(
    OUTPUT,
    index=False
)

print(f"Raw edges        : {len(raw):,}")
print(f"Resolved edges   : {resolved_count:,}")
print(f"Unresolved edges : {len(raw)-resolved_count:,}")
print()
print(f"Output : {OUTPUT.relative_to(REPOSITORY_ROOT)}")
print()
print("STEP202E COMPLETE")
