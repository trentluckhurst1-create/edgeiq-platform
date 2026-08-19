from pathlib import Path
from datetime import datetime
import shutil

path = Path(
    r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"
    r"\src\edgeiq-os\race\services\epiWorkspaceFeed.ts"
)

text = path.read_text(encoding="utf-8")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = path.with_name(
    f"{path.stem}_CHECKPOINT_BEFORE_RACE_KEY_NORMALISATION_{timestamp}{path.suffix}"
)
shutil.copy2(path, backup)

old_filter = """  const selectedRows = terminalRows.filter((row) => firstText(row.race_key) === firstText(raceKey));"""

new_filter = """  const incomingIdentity = canonicalRaceIdentity(raceKey, meetingKey);

  const selectedRows = terminalRows.filter((row) => {
    const exactMatch =
      firstText(row.race_key) === firstText(raceKey);

    if (exactMatch) return true;
    if (!incomingIdentity) return false;

    const rowIdentity = canonicalTerminalRaceIdentity(row);
    return Boolean(rowIdentity && rowIdentity === incomingIdentity);
  });"""

if old_filter not in text:
    raise SystemExit(
        "PATCH_ABORTED: exact selectedRows filter was not found. "
        "No file changes were made."
    )

helper_marker = """export function buildEpiWorkspaceViewModel("""

helpers = r'''
function normaliseRaceToken(input: unknown): string {
  return firstText(input)
    .toUpperCase()
    .replace(/&/g, " AND ")
    .replace(/[^A-Z0-9]+/g, "|")
    .replace(/^\|+|\|+$/g, "")
    .replace(/\|+/g, "|");
}

function canonicalTrackToken(input: unknown): string {
  const token = normaliseRaceToken(input);

  if (!token) return "";

  // Governed track-family aliases used by the current catalogue/feed.
  if (token.includes("SANDOWN")) return "SANDOWN";
  if (token.includes("MOE")) return "MOE";

  return token
    .split("|")
    .filter(Boolean)
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .filter((part) => part !== "RACE")
    .filter((part) => part !== "MEETING")
    .join("|");
}

function extractRaceDate(input: unknown): string {
  const raw = firstText(input);
  const match = raw.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  return match?.[1] ?? "";
}

function extractRaceNumber(input: unknown): string {
  const raw = firstText(input).toUpperCase();

  const labelled = raw.match(
    /(?:^|[^A-Z0-9])R(?:ACE)?[\s|:_-]*0*(\d{1,2})(?:$|[^0-9])/,
  );

  if (labelled?.[1]) {
    return String(Number(labelled[1]));
  }

  const normalised = normaliseRaceToken(raw).split("|");

  for (let index = normalised.length - 1; index >= 0; index -= 1) {
    const token = normalised[index];

    if (/^R\d{1,2}$/.test(token)) {
      return String(Number(token.slice(1)));
    }
  }

  return "";
}

function canonicalRaceIdentity(
  raceKey: unknown,
  meetingKey: unknown,
): string {
  const raceText = firstText(raceKey);
  const meetingText = firstText(meetingKey);
  const combined = [meetingText, raceText].filter(Boolean).join("|");

  const date =
    extractRaceDate(raceText) ||
    extractRaceDate(meetingText) ||
    extractRaceDate(combined);

  const raceNumber =
    extractRaceNumber(raceText) ||
    extractRaceNumber(combined);

  const meetingTrackSource = normaliseRaceToken(meetingText)
    .split("|")
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{2}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .join("|");

  const raceTrackSource = normaliseRaceToken(raceText)
    .split("|")
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{2}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .join("|");

  const track =
    canonicalTrackToken(meetingTrackSource) ||
    canonicalTrackToken(raceTrackSource);

  if (!date || !track || !raceNumber) return "";

  return `${date}|${track}|R${raceNumber}`;
}

function canonicalTerminalRaceIdentity(row: TerminalRow): string {
  const directKey = firstText(row.race_key);

  const directDate = extractRaceDate(directKey);
  const directRaceNumber = extractRaceNumber(directKey);

  const directParts = normaliseRaceToken(directKey).split("|");
  const directTrack = directParts
    .filter((part) => !/^\d{4}$/.test(part))
    .filter((part) => !/^\d{2}$/.test(part))
    .filter((part) => !/^\d{1,2}$/.test(part))
    .filter((part) => !/^R\d+$/.test(part))
    .join("|");

  const rowDate = firstText(
    (row as TerminalRow & { race_date?: string }).race_date,
  );

  const rowTrack = firstText(
    (row as TerminalRow & { track?: string }).track,
  );

  const rowRaceNumber = firstText(
    (row as TerminalRow & { race_no?: string }).race_no,
  ).replace(/^R/i, "");

  const date = rowDate || directDate;
  const track =
    canonicalTrackToken(rowTrack) ||
    canonicalTrackToken(directTrack);
  const raceNumber = rowRaceNumber || directRaceNumber;

  if (!date || !track || !raceNumber) return "";

  return `${date}|${track}|R${Number(raceNumber)}`;
}

'''

if helper_marker not in text:
    raise SystemExit(
        "PATCH_ABORTED: buildEpiWorkspaceViewModel marker was not found. "
        "No file changes were made."
    )

if "function canonicalRaceIdentity(" not in text:
    text = text.replace(helper_marker, helpers + helper_marker, 1)

text = text.replace(old_filter, new_filter, 1)

path.write_text(text, encoding="utf-8", newline="\n")

print(f"UPDATED={path}")
print(f"BACKUP={backup}")
print("EPI_RACE_KEY_NORMALISATION_PATCH_PASS")
