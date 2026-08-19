const env = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;

const configuredOrigin = (env.VITE_EDGEIQ_DATA_ORIGIN ?? "").trim().replace(/\/+$/, "");

export const EDGEIQ_DATA_ORIGIN = configuredOrigin;

export function edgeiqDataPath(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (!EDGEIQ_DATA_ORIGIN) {
    return normalizedPath;
  }

  return `${EDGEIQ_DATA_ORIGIN}${normalizedPath}`;
}
