import type { SyntheticEvent } from "react";

export const DEFAULT_SILK_URL = "/silks/default.svg";

export function hardHorseKey(value: unknown): string {
  return String(value ?? "")
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/\b(NZ|IRE|GB|USA|FR|JPN|SAF|GER|CAN|AUS)\b/g, " ")
    .replace(/[‘’'`]/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

export function silkSlug(value: unknown): string {
  return String(value ?? "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/\b(nz|ire|gb|usa|fr|jpn|saf|ger|can|aus)\b/g, " ")
    .replace(/[‘’'`]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function getSilksUrl(horse: unknown, explicitUrl?: unknown): string {
  const explicit = String(explicitUrl ?? "").trim();
  if (explicit && !/^https?:\/\//i.test(explicit)) return explicit;
  const slug = silkSlug(horse);
  return slug ? `/silks/${slug}.png` : DEFAULT_SILK_URL;
}

export function silkFallback(event: SyntheticEvent<HTMLImageElement>): void {
  const image = event.currentTarget;
  if (image.src.endsWith(DEFAULT_SILK_URL)) return;
  image.onerror = null;
  image.src = DEFAULT_SILK_URL;
}
