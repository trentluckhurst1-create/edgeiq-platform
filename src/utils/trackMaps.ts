export function getTrackMapSlug(trackName: string): string {
  const clean = String(trackName || "").toUpperCase().trim();

  const aliases: Record<string, string> = {
    "BALLARAT SYNTHETIC": "ballarat_synthetic",
    "PAKENHAM SYNTHETIC": "pakenham_synthetic",
    "PAKENHAM / TYNONG": "pakenham_tynong",
    "PAKENHAM TYNONG": "pakenham_tynong",
    "GEELONG SYNTHETIC": "geelong_synthetic",
    "GEELONG TURF": "geelong_turf",
    "MOONEE VALLEY": "moonee_valley",
    "YARRA VALLEY": "yarra_valley",
    "STONY CREEK": "stony_creek",
    "SWAN HILL": "swan_hill",
    "GREAT WESTERN": "great_western",
    "MT WYCHEPROOF": "mt_wycheproof",
    "ST ARNAUD": "st_arnaud",
  };

  return aliases[clean] || clean.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
