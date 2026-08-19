export const EDGEIQ_VIC_TRACKS = new Set([
  "MOE",
  "STAWELL",
  "HORSHAM",
  "FLEMINGTON",
  "CAULFIELD",
  "CAULFIELD HEATH",
  "MOONEE VALLEY",
  "SANDOWN",
  "PAKENHAM",
  "CRANBOURNE",
  "BALLARAT",
  "BENDIGO",
  "GEELONG",
  "SEYMOUR",
  "WARRNAMBOOL",
  "SALE",
  "MORNINGTON",
  "WANGARATTA",
  "WODONGA",
  "KILMORE",
  "KYNETON",
  "CASTERTON",
  "COLAC",
  "HAMILTON",
  "ARARAT",
  "TERANG",
  "SWAN HILL",
  "ECHUCA",
  "BENALLA",
  "BAIRNSDALE",
]);

export function isVicTrack(track?: string): boolean {
  const value = String(track ?? "").trim().toUpperCase();
  return EDGEIQ_VIC_TRACKS.has(value);
}
