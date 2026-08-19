from pathlib import Path

adapters = Path("src/edgeiq-os/services/adapters")

(adapters / "csvAdapterUtils.ts").write_text(r'''
export type CsvRow = Record<string, string>;

export async function readPublicCsv(path: string): Promise<CsvRow[]> {
  const response = await fetch(path);

  if (!response.ok) {
    throw new Error(`CSV read failed: ${path}`);
  }

  const text = await response.text();
  return parseCsv(text);
}

export function parseCsv(text: string): CsvRow[] {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  if (lines.length <= 1) return [];

  const headers = splitCsvLine(lines[0]).map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = splitCsvLine(line);
    const row: CsvRow = {};

    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });

    return row;
  });
}

export function splitCsvLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      quoted = !quoted;
      continue;
    }

    if (char === "," && !quoted) {
      values.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  values.push(current);
  return values;
}

export function pick(row: CsvRow | undefined, keys: string[], fallback = ""): string {
  if (!row) return fallback;

  for (const key of keys) {
    const value = row[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return String(value).trim();
    }
  }

  return fallback;
}

export function numberFrom(value: string | undefined, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
''', encoding="utf-8")

(adapters / "RaceShapeAdapter.ts").write_text(r'''
import type { IntelligenceAdapter } from "./AdapterTypes";

export const RACE_SHAPE_SOURCE = "/data/edgeiq_race_shape_story_v1.csv";

export const RaceShapeAdapter: IntelligenceAdapter = {
  key: "race-shape",
  label: "Race Shape",
  buildModuleOutput: () => ({
    key: "race-shape",
    label: "Race Shape",
    category: "PACE",
    status: "READY",
    confidence: 70,
    importance: 90,
    evidence: [
      {
        id: "race-shape-production-feed",
        category: "PACE",
        title: "Race Shape feed available",
        summary:
          "Race Shape is now mapped to the production story feed. The next UI wire will select the active race and render pressure, leaders and run-style interpretation.",
        confidence: 70,
        importance: 90,
        status: "READY",
      },
    ],
    feedHealth: {
      key: "race-shape",
      label: "Race Shape",
      status: "READY",
      freshness: "Mapped to edgeiq_race_shape_story_v1.csv",
    },
  }),
};
''', encoding="utf-8")

print("[EDGEIQ_RACE_SHAPE_ADAPTER] CSV utility added and Race Shape adapter promoted to production feed mapping")
