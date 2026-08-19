from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

utils = root / "src" / "utils" / "edgeiqFormat.ts"
utils.write_text('''export function text(v: unknown): string {
  return String(v ?? "").trim();
}

export function num(v: unknown): number | null {
  const s = text(v).replace(/[$,%]/g, "");
  if (!s || s === "-") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function cleanTrack(v: unknown): string {
  return text(v).toUpperCase().replace(/\\s+/g, " ").trim();
}

export function cleanHorse(v: unknown): string {
  return text(v).toUpperCase().replace(/\\s+/g, " ").trim();
}

export function cleanHorseLoose(v: unknown): string {
  return cleanHorse(v).replace(/[^A-Z0-9]/g, "");
}

export function money(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "-";
  return `$${v.toFixed(v < 10 ? 2 : 1)}`;
}

export function marketMoney(v: number | null): string {
  const value = money(v);
  return value === "$0.00" ? "-" : value;
}

export function pct(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "-";
  return `${v.toFixed(1)}%`;
}

export function signed(v: number | null, digits = 1): string {
  if (v === null || !Number.isFinite(v)) return "-";
  const prefix = v > 0 ? "+" : "";
  return `${prefix}${v.toFixed(digits)}`;
}
''', encoding="utf-8")

patterns = [
  r'\nfunction text\(v: unknown\): string \{.*?\n\}\n\s*\nfunction num\(v: unknown\): number \| null \{.*?\n\}\n\s*\nfunction cleanTrack\(v: unknown\): string \{.*?\n\}\n\s*\nfunction cleanHorse\(v: unknown\): string \{.*?\n\}\n\s*\nfunction cleanHorseLoose\(v: unknown\): string \{.*?\n\}\n',
  r'\nfunction money\(v: number \| null\): string \{.*?\n\}\n\s*\nfunction marketMoney\(v: number \| null\): string \{.*?\n\}\n\s*\nfunction pct\(v: number \| null\): string \{.*?\n\}\n',
  r'\nfunction signed\(v: number \| null, digits = 1\): string \{.*?\n\}\n',
]

for pattern in patterns:
    text, count = re.subn(pattern, "\n", text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"[ERROR] pattern not replaced: {pattern[:80]}")

import_line = 'import { cleanHorse, cleanHorseLoose, cleanTrack, marketMoney, money, num, pct, signed, text } from "../utils/edgeiqFormat";'

if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")

print("[FORMAT_HELPERS_EXTRACT] complete")
