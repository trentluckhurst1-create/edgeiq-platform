const assert = require("assert");
const {
  normaliseTrack,
  candidateUrls,
  collectRaceArrays,
  validateRaceFingerprints,
  meetingMatches,
} = require("./edgeiq_graphql_result_recovery_retry_6_v1.cjs");

assert.strictEqual(normaliseTrack("SPORTSBET-WANGARATTA"), "WANGARATTA");
assert.strictEqual(normaliseTrack("BetDeluxe Warracknabeal"), "WARRACKNABEAL");
assert.strictEqual(normaliseTrack("Southside Pakenham Synthetic"), "PAKENHAM SYNTHETIC");

const urls = candidateUrls({
  meeting_date: "2026-07-03",
  track: "WARRACKNABEAL",
  meeting_url: "https://www.racing.com/form/2026-07-03/betdeluxe-warracknabeal",
});
assert(urls.includes("https://www.racing.com/form/2026-07-03/warracknabeal"));

const raceArrays = collectRaceArrays({ data: { getRacesForMeet: [{ raceNumber: 1, formRaceEntries: [{ horseName: "A" }] }] } });
assert.strictEqual(raceArrays.length, 1);
assert.strictEqual(raceArrays[0][0].raceNumber, 1);

const match = meetingMatches(
  { meeting_date: "2026-07-04", track: "SPORTSBET-WANGARATTA" },
  { date: "2026-07-04", trackName: "Wangaratta" },
  []
);
assert.strictEqual(match.ok, true);

const fpFailures = validateRaceFingerprints([
  { race_date: "2026-01-01", track: "Track", race_no: "1", finish: "1", horse: "Same" },
  { race_date: "2026-01-01", track: "Track", race_no: "2", finish: "1", horse: "Same" },
]);
assert.strictEqual(fpFailures.length, 1);

console.log("EDGEIQ_RECOVERY_RETRY_6_UNIT_GUARDS=PASS");
