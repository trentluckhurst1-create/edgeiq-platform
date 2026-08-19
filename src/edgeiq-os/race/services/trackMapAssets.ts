export type EdgeiqTrackMapAsset = {
  canonicalTrack: string;
  assetPath: string;
};

const TRACK_MAP_ASSETS: Record<string, EdgeiqTrackMapAsset> = {
  ALEXANDRA: { canonicalTrack: "Alexandra", assetPath: "/track-maps/Alexandra.png" },
  ARARAT: { canonicalTrack: "Ararat", assetPath: "/track-maps/Ararat.png" },
  AVOCA: { canonicalTrack: "Avoca", assetPath: "/track-maps/Avoca.png" },
  BAIRNSDALE: { canonicalTrack: "Bairnsdale", assetPath: "/track-maps/Bairnsdale.png" },
  BALLARAT: { canonicalTrack: "Ballarat", assetPath: "/track-maps/Ballarat.png" },
  BALNARRING: { canonicalTrack: "Balnarring", assetPath: "/track-maps/Balnarring.png" },
  BENALLA: { canonicalTrack: "Benalla", assetPath: "/track-maps/Benalla.png" },
  BENDIGO: { canonicalTrack: "Bendigo", assetPath: "/track-maps/Bendigo.png" },
  BUCHAN: { canonicalTrack: "Buchan", assetPath: "/track-maps/Buchan.png" },
  BURRUMBEET: { canonicalTrack: "Burrumbeet", assetPath: "/track-maps/Burrumbeet.png" },
  CAMPERDOWN: { canonicalTrack: "Camperdown", assetPath: "/track-maps/Camperdown.png" },
  CASTERTON: { canonicalTrack: "Casterton", assetPath: "/track-maps/Casterton.png" },
  CAULFIELD: { canonicalTrack: "Caulfield", assetPath: "/track-maps/Caulfield.png" },
  COLAC: { canonicalTrack: "Colac", assetPath: "/track-maps/Colac.png" },
  COLERAINE: { canonicalTrack: "Coleraine", assetPath: "/track-maps/Coleraine.png" },
  CRANBOURNE: { canonicalTrack: "Cranbourne", assetPath: "/track-maps/Cranbourne.png" },
  DEDERANG: { canonicalTrack: "Dederang", assetPath: "/track-maps/Dederang.png" },
  DONALD: { canonicalTrack: "Donald", assetPath: "/track-maps/Donald.png" },
  DROUIN: { canonicalTrack: "Drouin", assetPath: "/track-maps/Drouin.png" },
  DUNKELD: { canonicalTrack: "Dunkeld", assetPath: "/track-maps/Dunkeld.png" },
  ECHUCA: { canonicalTrack: "Echuca", assetPath: "/track-maps/Echuca.png" },
  EDENHOPE: { canonicalTrack: "Edenhope", assetPath: "/track-maps/Edenhope.png" },
  FLEMINGTON: { canonicalTrack: "Flemington", assetPath: "/track-maps/Flemington.png" },
  GEELONGSYNTHETIC: { canonicalTrack: "Geelong Synthetic", assetPath: "/track-maps/Geelong_Synthetic.png" },
  GEELONGTURF: { canonicalTrack: "Geelong Turf", assetPath: "/track-maps/Geelong_Turf.png" },
  GREATWESTERN: { canonicalTrack: "Great Western", assetPath: "/track-maps/Great_Western.png" },
  GUNBOWER: { canonicalTrack: "Gunbower", assetPath: "/track-maps/Gunbower.png" },
  HAMILTON: { canonicalTrack: "Hamilton", assetPath: "/track-maps/Hamilton.png" },
  HANGINGROCK: { canonicalTrack: "Hanging Rock", assetPath: "/track-maps/Hanging_Rock.png" },
  HEALESVILLE: { canonicalTrack: "Healesville", assetPath: "/track-maps/Healesville.png" },
  HORSHAM: { canonicalTrack: "Horsham", assetPath: "/track-maps/Horsham.png" },
  KERANG: { canonicalTrack: "Kerang", assetPath: "/track-maps/Kerang.png" },
  KILMORE: { canonicalTrack: "Kilmore", assetPath: "/track-maps/Kilmore.png" },
  KYNETON: { canonicalTrack: "Kyneton", assetPath: "/track-maps/Kyneton.png" },
  MANANGATANG: { canonicalTrack: "Manangatang", assetPath: "/track-maps/Manangatang.png" },
  MANSFIELD: { canonicalTrack: "Mansfield", assetPath: "/track-maps/Mansfield.png" },
  MERTON: { canonicalTrack: "Merton", assetPath: "/track-maps/Merton.png" },
  MILDURA: { canonicalTrack: "Mildura", assetPath: "/track-maps/Mildura.png" },
  MOE: { canonicalTrack: "Moe", assetPath: "/track-maps/Moe.png" },
  MOONEEVALLEY: { canonicalTrack: "Moonee Valley", assetPath: "/track-maps/Moonee_Valley.png" },
  MORNINGTON: { canonicalTrack: "Mornington", assetPath: "/track-maps/Mornington.png" },
  MORTLAKE: { canonicalTrack: "Mortlake", assetPath: "/track-maps/Mortlake.png" },
  MTWYCHEPROOF: { canonicalTrack: "Mt Wycheproof", assetPath: "/track-maps/Mt_Wycheproof.png" },
  MURTOA: { canonicalTrack: "Murtoa", assetPath: "/track-maps/Murtoa.png" },
  NHILL: { canonicalTrack: "Nhill", assetPath: "/track-maps/Nhill.png" },
  OMEO: { canonicalTrack: "Omeo", assetPath: "/track-maps/Omeo.png" },
  PAKENHAMTYNONGSYNTHETIC: { canonicalTrack: "Pakenham Tynong Synthetic", assetPath: "/track-maps/Pakenham_Tynong_Synthetic.png" },
  PAKENHAMTYNONGTURF: { canonicalTrack: "Pakenham Tynong Turf", assetPath: "/track-maps/Pakenham_Tynong_Turf.png" },
  PENSHURST: { canonicalTrack: "Penshurst", assetPath: "/track-maps/Penshurst.png" },
  SALE: { canonicalTrack: "Sale", assetPath: "/track-maps/Sale.png" },
  SANDOWN: { canonicalTrack: "Sandown", assetPath: "/track-maps/Sandown.png" },
  SEYMOUR: { canonicalTrack: "Seymour", assetPath: "/track-maps/Seymour.png" },
  STARNAUD: { canonicalTrack: "St Arnaud", assetPath: "/track-maps/St_Arnaud.png" },
  STAWELL: { canonicalTrack: "Stawell", assetPath: "/track-maps/Stawell.png" },
  STONYCREEK: { canonicalTrack: "Stony Creek", assetPath: "/track-maps/Stony_Creek.png" },
  SWANHILL: { canonicalTrack: "Swan Hill", assetPath: "/track-maps/Swan_Hill.png" },
  SWIFTSCREEK: { canonicalTrack: "Swifts Creek", assetPath: "/track-maps/Swifts_Creek.png" },
  TATURA: { canonicalTrack: "Tatura", assetPath: "/track-maps/Tatura.png" },
  TERANG: { canonicalTrack: "Terang", assetPath: "/track-maps/Terang.png" },
  TOWONG: { canonicalTrack: "Towong", assetPath: "/track-maps/Towong.png" },
  TRARALGON: { canonicalTrack: "Traralgon", assetPath: "/track-maps/Traralgon.png" },
  WANGARATTA: { canonicalTrack: "Wangaratta", assetPath: "/track-maps/Wangaratta.png" },
  WARRACKNABEAL: { canonicalTrack: "Warracknabeal", assetPath: "/track-maps/Warracknabeal.png" },
  WARRNAMBOOL: { canonicalTrack: "Warrnambool", assetPath: "/track-maps/Warrnambool.png" },
  WERRIBEE: { canonicalTrack: "Werribee", assetPath: "/track-maps/Werribee.png" },
  WODONGA: { canonicalTrack: "Wodonga", assetPath: "/track-maps/Wodonga.png" },
  WOOLAMAI: { canonicalTrack: "Woolamai", assetPath: "/track-maps/Woolamai.png" },
  YARRAVALLEY: { canonicalTrack: "Yarra Valley", assetPath: "/track-maps/Yarra_Valley.png" },
  YEA: { canonicalTrack: "Yea", assetPath: "/track-maps/Yea.png" },
};

const TRACK_MAP_ALIASES: Record<string, string> = {
  GEELONG: "GEELONGTURF",
  GEELONGSYNTH: "GEELONGSYNTHETIC",
  MOONEEVALLEYRACECOURSE: "MOONEEVALLEY",
  MOUNTWYCHEPROOF: "MTWYCHEPROOF",
  PAKENHAM: "PAKENHAMTYNONGTURF",
  PAKENHAMSYNTH: "PAKENHAMTYNONGSYNTHETIC",
  PAKENHAMSYNTHETIC: "PAKENHAMTYNONGSYNTHETIC",
  PAKENHAMTURF: "PAKENHAMTYNONGTURF",
  PAKENHAMTYNONG: "PAKENHAMTYNONGTURF",
  SANDOWNH: "SANDOWN",
  SANDOWNHILLSIDE: "SANDOWN",
  SANDOWNL: "SANDOWN",
  SANDOWNLAKESIDE: "SANDOWN",
  THEVALLEY: "MOONEEVALLEY",
};

function normaliseTrackKey(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/&/g, "AND")
    .replace(/\bRACECOURSE\b/g, "")
    .replace(/\bRACING\b/g, "")
    .replace(/\bVICTORIA\b/g, "")
    .replace(/\bVIC\b/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

export function resolveTrackMapAsset(
  trackName: unknown,
  surfaceName?: unknown,
): EdgeiqTrackMapAsset | null {
  const trackKey = normaliseTrackKey(trackName);
  const surfaceKey = normaliseTrackKey(surfaceName);
  const combinedKey = `${trackKey}${surfaceKey}`;

  const combinedAlias = TRACK_MAP_ALIASES[combinedKey];
  const trackAlias = TRACK_MAP_ALIASES[trackKey];

  return (
    TRACK_MAP_ASSETS[combinedKey] ??
    (combinedAlias ? TRACK_MAP_ASSETS[combinedAlias] : undefined) ??
    TRACK_MAP_ASSETS[trackKey] ??
    (trackAlias ? TRACK_MAP_ASSETS[trackAlias] : undefined) ??
    null
  );
}

export function resolveTrackMapPath(
  trackName: unknown,
  surfaceName?: unknown,
): string | null {
  return resolveTrackMapAsset(trackName, surfaceName)?.assetPath ?? null;
}
