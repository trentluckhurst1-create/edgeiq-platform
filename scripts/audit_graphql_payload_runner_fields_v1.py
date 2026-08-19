from pathlib import Path
import json

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PAYLOAD = ROOT / "public" / "data" / "edgeiq_graphql_getRacesForMeet_payload_v1.json"
OUT = ROOT / "docs" / "graphql_payload_runner_field_audit_v1.txt"

if not PAYLOAD.exists():
    raise SystemExit(f"Payload not found: {PAYLOAD}")

payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))

races = (((payload.get("data") or {}).get("getRacesForMeet")) or [])

report = []
report.append("EDGEIQ GRAPHQL PAYLOAD AUDIT")
report.append("=" * 120)
report.append(f"Payload: {PAYLOAD}")
report.append(f"Race objects: {len(races)}")
report.append("")

runner_count = 0

for race in races:
    meet = race.get("meet") or {}
    entries = race.get("formRaceEntries") or []

    report.append("=" * 120)
    report.append(f"MEETING : {meet.get('name')}")
    report.append(f"STATE   : {meet.get('state')}")
    report.append(f"RACE    : {race.get('raceNumber')}")
    report.append(f"RUNNERS : {len(entries)}")
    report.append("")

    for e in entries:
        runner_count += 1
        report.append(f"HORSE    : {e.get('horseName')}")
        report.append(f"TRAINER  : {e.get('trainerName')}")
        report.append(f"JOCKEY   : {e.get('jockeyName')}")
        report.append(f"BARRIER  : {e.get('barrierNumber')}")
        report.append(f"LIVE BAR : {e.get('liveBarrierNumber')}")
        report.append(f"WEIGHT   : {e.get('weight')}")
        report.append(f"SCRATCH  : {e.get('scratched')}")
        report.append("")

report.append("=" * 120)
report.append(f"TOTAL RUNNERS: {runner_count}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print("")
print(f"OUTPUT={OUT}")
print("GRAPHQL_PAYLOAD_AUDIT_COMPLETE")
