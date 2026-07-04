export function text(v: unknown): string {
  return String(v ?? "").trim();
}

export function num(v: unknown): number | null {
  const s = text(v).replace(/[$,%]/g, "");
  if (!s || s === "-") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function cleanTrack(v: unknown): string {
  return text(v).toUpperCase().replace(/\s+/g, " ").trim();
}

export function cleanHorse(v: unknown): string {
  return text(v).toUpperCase().replace(/\s+/g, " ").trim();
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
