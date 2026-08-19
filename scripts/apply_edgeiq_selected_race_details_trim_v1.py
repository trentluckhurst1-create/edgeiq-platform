from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"

text = path.read_text(encoding="utf-8")
original = text

anchor = '''  return (
    <section className="eiq-meeting-v1-panel">
      <header>
        <div>
          <span>Selected Race Details</span>
          <strong>{selected.row.raceLabel} - {selected.row.raceName}</strong>
          {selected.row.secondary ? <p>{selected.row.secondary}</p> : null}
        </div>
      </header>
      <DetailGrid details={selected.details} />
'''

replacement = '''  const visibleDetails = selected.details.filter(
    (detail) =>
      ![
        "AGE / SEX",
        "WEIGHT CONDITIONS",
        "ACCEPTANCES",
        "SCRATCHINGS",
        "MARKET STATUS",
        "DATA COVERAGE",
      ].includes(detail.label.trim().toUpperCase()),
  );

  return (
    <section className="eiq-meeting-v1-panel">
      <header>
        <div>
          <span>Selected Race Details</span>
          <strong>{selected.row.raceLabel} - {selected.row.raceName}</strong>
          {selected.row.secondary ? <p>{selected.row.secondary}</p> : null}
        </div>
      </header>
      <DetailGrid details={visibleDetails} />
'''

count = text.count(anchor)

if count != 1:
    raise RuntimeError(
        f"Expected one Selected Race Details anchor, found {count}. "
        "No file was written."
    )

text = text.replace(anchor, replacement, 1)

if "<DetailGrid details={selected.details} />" in text:
    raise RuntimeError(
        "Original unfiltered Selected Race Details render still remains."
    )

for required in (
    '"AGE / SEX"',
    '"WEIGHT CONDITIONS"',
    '"ACCEPTANCES"',
    '"SCRATCHINGS"',
    '"MARKET STATUS"',
    '"DATA COVERAGE"',
    "<DetailGrid details={visibleDetails} />",
):
    if required not in text:
        raise RuntimeError(f"Patch validation failed: {required}")

if text == original:
    raise RuntimeError("No source changes were produced.")

path.write_text(text, encoding="utf-8")

print("EDGEIQ_SELECTED_RACE_DETAILS_TRIM_V1_APPLIED")
print("removed=AGE_SEX")
print("removed=WEIGHT_CONDITIONS")
print("removed=ACCEPTANCES")
print("removed=SCRATCHINGS")
print("removed=MARKET_STATUS")
print("removed=DATA_COVERAGE")
print(f"path={path}")
