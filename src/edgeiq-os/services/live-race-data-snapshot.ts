export type LiveRaceRunnerSnapshot = {
  runner: string;
  trainer?: string;
  jockey?: string;
  barrier?: string;
  weight?: string;
  market?: string;
  runnerDNA?: string;
  dnaScore?: string;
  dnaBand?: string;
  edgeRating?: string;
  formUrl?: string;
};

export const LIVE_RACE_DATA_SOURCE = "public\\data\\edgeiq_live_runner_board_v7_1_current_day_candidate.csv";
export const LIVE_RACE_DNA_SOURCE = "public\\data\\edgeiq_runner_dna_v6_2.csv";

export const liveRaceRunnerSnapshot: LiveRaceRunnerSnapshot[] = [
  { runner: "LIMBERING", trainer: "RAHARNA MCDONALD", jockey: "Not Notified", barrier: "11", weight: "", market: "SCRATCHED", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "", formUrl: "" },
  { runner: "HUGHIE", trainer: "JAMIE EDWARDS", jockey: "Not Notified", barrier: "15", weight: "", market: "SCRATCHED", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "", formUrl: "" },
  { runner: "DETERMINATO", trainer: "DOMINIC SUTTON", jockey: "BILLY EGAN", barrier: "1", weight: "", market: "4.8", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "65.64", formUrl: "" },
  { runner: "KING TAGALOA", trainer: "JULIUS SANDHU", jockey: "DYLAN DEAN", barrier: "4", weight: "", market: "18", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "49.72", formUrl: "" },
  { runner: "OBON", trainer: "MICHAEL KENT", jockey: "LUKE NOLEN", barrier: "3", weight: "", market: "2.9", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "62.96", formUrl: "" },
  { runner: "REEL DEADLY", trainer: "CIARON MAHER", jockey: "THOMAS STOCKDALE", barrier: "6", weight: "", market: "10", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "50.75", formUrl: "" },
  { runner: "RUSSIAN FIREBIRD", trainer: "TOBY LAKE", jockey: "BRAD RAWILLER", barrier: "2", weight: "", market: "41", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "53.7", formUrl: "" },
  { runner: "SKY DEEL", trainer: "GAVIN BEDGGOOD", jockey: "JAMIE MOTT", barrier: "7", weight: "", market: "12", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "58.73", formUrl: "" },
  { runner: "EXPANDING POWER", trainer: "ENVER JUSUFOVIC", jockey: "LACHLAN NEINDORF", barrier: "5", weight: "", market: "2.25", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "62.04", formUrl: "" },
  { runner: "CAPITAL STORM", trainer: "PHILLIP STOKES", jockey: "LACHLAN NEINDORF", barrier: "13", weight: "", market: "TAB_FIXED_WIN", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "0", formUrl: "" },
  { runner: "FONTALICIOUS", trainer: "SHANE NICHOLS & HAYDEN BLACK", jockey: "PATRICK MOLONEY", barrier: "2", weight: "", market: "13", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "57.33", formUrl: "" },
  { runner: "MERCHANTESSA", trainer: "JASON WARREN", jockey: "TEO NUGENT", barrier: "12", weight: "", market: "TAB_FIXED_WIN", runnerDNA: "POOR", dnaScore: "12.5", dnaBand: "POOR", edgeRating: "0", formUrl: "" },
  { runner: "MIRADOR", trainer: "BEN, WILL & JD HAYES", jockey: "DANIEL STACKHOUSE", barrier: "8", weight: "", market: "3.4", runnerDNA: "POOR", dnaScore: "28.2", dnaBand: "POOR", edgeRating: "64.63", formUrl: "" },
  { runner: "RUBY GUILD", trainer: "ROBBIE GRIFFITHS", jockey: "NATHAN PUNCH", barrier: "4", weight: "", market: "8.5", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "0", formUrl: "" },
  { runner: "TRICKY MISS", trainer: "CIARON MAHER", jockey: "JAKE NOONAN", barrier: "7", weight: "", market: "26", runnerDNA: "POOR", dnaScore: "14.4", dnaBand: "POOR", edgeRating: "0", formUrl: "" },
  { runner: "PORTINARI", trainer: "BEN, WILL & JD HAYES", jockey: "DANIEL STACKHOUSE", barrier: "9", weight: "", market: "4", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "59.13", formUrl: "" },
  { runner: "MINELLO", trainer: "ANTHONY & SAM FREEDMAN", jockey: "JAMIE MOTT", barrier: "6", weight: "", market: "12", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "0", formUrl: "" },
  { runner: "PINAMILLOY", trainer: "JASON WARREN", jockey: "ZAC SPAIN", barrier: "10", weight: "", market: "16", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "56", formUrl: "" },
  { runner: "RES MIRA", trainer: "MARK WEBB", jockey: "BRAD RAWILLER", barrier: "11", weight: "", market: "61", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "0", formUrl: "" },
  { runner: "STINGRAY BARB", trainer: "PAT CAREY & HARRIS WALKER", jockey: "NADIA DANIELS", barrier: "12", weight: "", market: "101", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "41", formUrl: "" },
  { runner: "ZAAC", trainer: "JOHN MCARDLE", jockey: "THOMAS STOCKDALE", barrier: "2", weight: "", market: "TAB_FIXED_WIN", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "3", formUrl: "" },
  { runner: "BABY BLUE", trainer: "BEN, WILL & JD HAYES", jockey: "DAMIEN THORNTON", barrier: "5", weight: "", market: "12", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "0", formUrl: "" },
  { runner: "CONTARINI", trainer: "CHRIS WALLER", jockey: "BEAU MERTENS", barrier: "3", weight: "", market: "12", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "0", formUrl: "" },
  { runner: "ETERNAL JOY", trainer: "BEN, WILL & JD HAYES", jockey: "JORDAN CHILDS", barrier: "1", weight: "", market: "5", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "64.0", formUrl: "" },
  { runner: "BIG FIN", trainer: "BROOKE VERWEY-MITCHELL", jockey: "TEO NUGENT", barrier: "9", weight: "", market: "151", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "50.75", formUrl: "" },
  { runner: "LEVRIER", trainer: "MATT LAURIE", jockey: "PATRICK MOLONEY", barrier: "3", weight: "", market: "7", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "65.82", formUrl: "" },
  { runner: "MARCH ON BY", trainer: "SIMON ZAHRA", jockey: "RYAN HOUSTON", barrier: "1", weight: "", market: "26", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "51.84", formUrl: "" },
  { runner: "BLUE SHIELD", trainer: "MICK PRICE & MICHAEL KENT JNR", jockey: "LACHLAN NEINDORF", barrier: "2", weight: "", market: "1.95", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "65.76", formUrl: "" },
  { runner: "CALEXPO", trainer: "BEN, WILL & JD HAYES", jockey: "DANIEL STACKHOUSE", barrier: "2", weight: "", market: "TAB_FIXED_WIN", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "41", formUrl: "" },
  { runner: "CIRCUS BERZERKUS", trainer: "JIM CERCHI (JNR)", jockey: "BAILEY KINNINMONT", barrier: "8", weight: "", market: "151", runnerDNA: "", dnaScore: "", dnaBand: "", edgeRating: "1", formUrl: "" }
];

export function normaliseRunnerName(value: string | undefined | null): string {
  return String(value ?? "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, " ");
}

export function findLiveRunnerSnapshot(runner: string | undefined | null): LiveRaceRunnerSnapshot | undefined {
  const key = normaliseRunnerName(runner);
  return liveRaceRunnerSnapshot.find((item) => normaliseRunnerName(item.runner) === key);
}
