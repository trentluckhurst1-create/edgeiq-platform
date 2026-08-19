import csv
import hashlib
from pathlib import Path

repos = {
    "EDGEIQ_PLATFORM": Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"),
    "EDGEIQ_PLATFORM_CLEAN": Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM_CLEAN"),
    "HORSE_RACING_MODEL": Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model"),
    "CHECKPOINTS": Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\checkpoints")
}

extensions = {".py",".ts",".tsx",".json",".csv",".md",".ps1",".txt"}

output = repos["EDGEIQ_PLATFORM"] / "repository_inventory.csv"

def sha256(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b = f.read(1024*1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

rows=[]

for repo,root in repos.items():

    if not root.exists():
        print(f"Missing: {root}")
        continue

    print(f"Scanning {repo}")

    for f in root.rglob("*"):

        if not f.is_file():
            continue

        if f.suffix.lower() not in extensions:
            continue

        try:
            s=f.stat()

            rows.append({
                "Repository":repo,
                "RelativePath":str(f.relative_to(root)),
                "Extension":f.suffix.lower(),
                "Size":s.st_size,
                "Modified":s.st_mtime,
                "SHA256":sha256(f)
            })
        except Exception:
            pass

with open(output,"w",newline="",encoding="utf8") as fp:

    writer=csv.DictWriter(fp,fieldnames=[
        "Repository",
        "RelativePath",
        "Extension",
        "Size",
        "Modified",
        "SHA256"
    ])

    writer.writeheader()
    writer.writerows(rows)

print()
print("="*60)
print("Inventory complete")
print(output)
print("Files:",len(rows))
print("="*60)
