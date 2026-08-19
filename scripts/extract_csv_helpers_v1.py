from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

utils = root / "src" / "utils" / "edgeiqCsv.ts"
utils.write_text('''export type CsvRow = Record<string, string>;

const FRONTEND_CSV_ROW_LIMIT = 10000;

export function csvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let quoted = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    const next = line[i + 1];

    if (ch === '"' && quoted && next === '"') {
      cur += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (ch === "," && !quoted) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }

  out.push(cur);
  return out;
}

export function parseCsv(raw: string, sourcePath = "CSV feed"): CsvRow[] {
  const lines = raw.replace(/^\\uFEFF/, "").split(/\\r?\\n/).filter((x) => x.trim());

  if (!lines.length) return [];

  if (lines.length - 1 > FRONTEND_CSV_ROW_LIMIT) {
    console.warn(`[EDGEiQ] Skipping oversized frontend CSV feed: ${sourcePath} (${lines.length - 1} rows > ${FRONTEND_CSV_ROW_LIMIT})`);
    return [];
  }

  const headers = csvLine(lines[0]).map((h) => h.trim());

  return lines.slice(1).map((line) => {
    const cells = csvLine(line);
    const row: CsvRow = {};
    headers.forEach((header, index) => {
      row[header] = String(cells[index] ?? "").trim();
    });
    return row;
  });
}

export async function loadCsv(path: string): Promise<CsvRow[]> {
  try {
    const res = await fetch(`${path}?v=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) return [];
    return parseCsv(await res.text(), path);
  } catch {
    return [];
  }
}
''', encoding="utf-8")

pattern = r'\nfunction csvLine\(line: string\): string\[\] \{.*?\n\}\n\s*\nconst FRONTEND_CSV_ROW_LIMIT = 10000;\n\s*\nfunction parseCsv\(raw: string, sourcePath = "CSV feed"\): Row\[\] \{.*?\n\}\n\s*\nasync function loadCsv\(path: string\): Promise<Row\[\]> \{.*?\n\}\n'

text, count = re.subn(pattern, "\n", text, count=1, flags=re.S)
if count != 1:
    raise SystemExit("[ERROR] CSV helper block not replaced")

import_line = 'import { loadCsv, parseCsv, type CsvRow } from "../utils/edgeiqCsv";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

text = text.replace("type Row = Record<string, string>;", "type Row = CsvRow;")

path.write_text(text, encoding="utf-8")

print("[CSV_HELPERS_EXTRACT] complete")
