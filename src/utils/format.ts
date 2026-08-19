export function toNumber(value: unknown, fallback = 0): number {
  if (value === null || value === undefined || value === "") return fallback;
  const n = Number(String(value).replace(/[^0-9.\-]/g, ""));
  return Number.isFinite(n) ? n : fallback;
}

export function toText(value: unknown, fallback = ""): string {
  if (value === null || value === undefined) return fallback;
  return String(value).trim();
}

export function safeLower(value: unknown): string {
  return toText(value).toLowerCase();
}

export function formatPrice(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "-";
  return value.toFixed(2);
}

export function formatPct(value: number): string {
  if (!Number.isFinite(value)) return "-";
  return `${value.toFixed(1)}%`;
}

export function formatMargin(value: number): string {
  if (!Number.isFinite(value)) return "-";
  return value.toFixed(1);
}


