const env = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;

const configuredOrigin = (env.VITE_EDGEIQ_DATA_ORIGIN ?? "").trim().replace(/\/+$/, "");

export const EDGEIQ_DATA_ORIGIN = configuredOrigin;

export function edgeiqDataPath(path: string): string {
  const normalizedPath = path.replace(/^\/+/, "");

  if (EDGEIQ_DATA_ORIGIN) {
    return `${EDGEIQ_DATA_ORIGIN}/${normalizedPath}`;
  }

  // Respect Vite's deployment base. On GitHub Pages the application lives at
  // /edgeiq-platform/, so root-absolute /data/... URLs incorrectly request data
  // from trentluckhurst1-create.github.io/data/... and bypass the repository.
  const baseUrl = (env.BASE_URL ?? "/").replace(/\/+$/, "/");
  return `${baseUrl}${normalizedPath}`;
}
