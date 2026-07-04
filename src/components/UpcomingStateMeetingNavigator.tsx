import React, { useEffect, useMemo, useState } from 'react';

type CsvRow = Record<string, string>;

type RunnerRow = {
  raceDate: string;
  state: string;
  track: string;
  raceNo: number;
  horse: string;
  horseKey: string;
  horseNo?: number;
  barrier: string;
  jockey: string;
  trainer: string;
  ratedPrice?: number;
  marketPrice?: number;
  edgePct?: number;
  silkUrl: string;
  scratched: boolean;
  mapComment: string;
  speedMapGroup: string;
  speedMapRank?: number;
  weight: string;
  raw: CsvRow;
};

type FormRun = {
  id: string;
  horseKey: string;
  horse: string;
  runDate: string;
  track: string;
  distance: string;
  raceClass: string;
  barrier: string;
  jockey: string;
  finishPos: string;
  margin: string;
  sp: string;
  trackCondition: string;
  runRating?: number;
  raw: CsvRow;
};

type FormSummary = {
  horseKey: string;
  horse: string;
  lastRating?: number;
  avgLast3?: number;
  peakRating?: number;
  starts?: number;
  raw: CsvRow;
};

type MeetingGroup = {
  key: string;
  state: string;
  raceDate: string;
  track: string;
  races: number[];
};

const STATE_ORDER = ['VIC', 'NSW', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'];

function firstNonEmpty(row: CsvRow | undefined, keys: string[]): string {
  if (!row) return '';
  for (const key of keys) {
    const value = row[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return String(value).trim();
    }
  }
  return '';
}

function firstFromRows(rows: Array<CsvRow | undefined>, keys: string[]): string {
  for (const row of rows) {
    const value = firstNonEmpty(row, keys);
    if (value) return value;
  }
  return '';
}

function toNumber(value: unknown): number | undefined {
  if (value === undefined || value === null) return undefined;
  const s = String(value).replace(/[$,%]/g, '').trim();
  if (!s) return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
}

function normalizeHorseKey(value: string): string {
  return String(value || '')
    .toUpperCase()
    .replace(/^\d+\.\s*/, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/[^A-Z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizeTrack(value: string): string {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function formatDateKey(value: string): string {
  return String(value || '').trim().slice(0, 10);
}

function formatOdds(value?: number): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '';
  return `$${value >= 10 ? value.toFixed(1) : value.toFixed(2)}`;
}

function formatPct(value?: number): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '0.0%';
  return `${value.toFixed(1)}%`;
}

function formatFigure(value?: number): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '';
  return value.toFixed(1);
}

function getTodayIsoLocal(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function isTruthy(value: string): boolean {
  const s = String(value || '').trim().toLowerCase();
  return s === 'true' || s === '1' || s === 'yes' || s === 'y';
}

function compareDateDesc(a: string, b: string): number {
  return String(b || '').localeCompare(String(a || ''));
}

function compactMoney(value: string): string {
  if (!value) return '';
  const n = toNumber(value);
  if (n === undefined) return value;
  return `$${Math.round(n).toLocaleString()}`;
}

function cleanMaybeMoneyJockey(value: string): string {
  if (!value) return '';
  return value.replace(/\(\$[\d,]+\)\s*/g, '').trim() || '';
}

function joinBits(bits: string[], separator = '   '): string {
  return bits.filter(Boolean).join(separator);
}

function buildProfileLines(
  runner: RunnerRow,
  summary: FormSummary | undefined
): {
  heading: string;
  meta1: string;
  meta2: string;
  meta3: string;
  records1: string;
  records2: string;
  records3: string;
  colours: string;
  gear: string;
} {
  const rows = [summary?.raw, runner.raw];

  const horseNo = firstFromRows(rows, ['horse_no', 'runner_no', 'number']);
  const age = firstFromRows(rows, ['age']);
  const sex = firstFromRows(rows, ['sex']);
  const colour = firstFromRows(rows, ['colour', 'color']);
  const dob = firstFromRows(rows, ['foaled', 'dob', 'date_of_birth', 'birth_date']);
  const sire = firstFromRows(rows, ['sire']);
  const dam = firstFromRows(rows, ['dam']);
  const damSire = firstFromRows(rows, ['dam_sire', 'damsire']);
  const trainer = firstFromRows(rows, ['trainer']);
  const jockey = firstFromRows(rows, ['jockey']);
  const weight = firstFromRows(rows, ['weight', 'weight_carried']);
  const barrier = firstFromRows(rows, ['barrier']);
  const record = firstFromRows(rows, ['record', 'career_record_text', 'career_record']);
  const prizeMoney = compactMoney(firstFromRows(rows, ['prize_money']));
  const firstUp = firstFromRows(rows, ['first_up_record', 'first_up']);
  const secondUp = firstFromRows(rows, ['second_up_record', 'second_up']);
  const trackRec = firstFromRows(rows, ['track_record', 'track']);
  const distRec = firstFromRows(rows, ['dist_record', 'distance_record']);
  const trackDist = firstFromRows(rows, ['track_dist_record', 'track_distance_record']);
  const distanceWins = firstFromRows(rows, ['distance_wins', 'distance_s_won']);
  const firmRec = firstFromRows(rows, ['firm_record', 'firm']);
  const goodRec = firstFromRows(rows, ['good_record', 'good']);
  const softRec = firstFromRows(rows, ['soft_record', 'soft']);
  const heavyRec = firstFromRows(rows, ['heavy_record', 'heavy']);
  const synthRec = firstFromRows(rows, ['synthetic_record', 'synthetic']);
  const colours = firstFromRows(rows, ['colours', 'colors']);
  const gear = firstFromRows(rows, ['gear_changes', 'gear', 'gear_change']);

  const heading = joinBits([horseNo ? `${horseNo}` : '', runner.horse], ' ');

  const meta1 = joinBits([
    age ? `${age} year old` : '',
    colour || '',
    sex || '',
    dob ? `(${dob})` : '',
    sire ? `Sire: ${sire}` : '',
    dam ? `Dam: ${dam}${damSire ? ` (${damSire})` : ''}` : '',
  ]);

  const meta2 = joinBits([
    trainer ? `Trainer: ${trainer}` : '',
    jockey ? `Jockey: ${jockey}` : '',
    weight ? `${weight}` : '',
    barrier ? `Barrier: ${barrier}` : '',
  ]);

  const meta3 = joinBits([
    summary?.starts !== undefined ? `Starts: ${summary.starts}` : '',
    summary?.lastRating !== undefined ? `Last: ${formatFigure(summary.lastRating)}` : '',
    summary?.avgLast3 !== undefined ? `Avg L3: ${formatFigure(summary.avgLast3)}` : '',
    summary?.peakRating !== undefined ? `Peak: ${formatFigure(summary.peakRating)}` : '',
  ]);

  const records1 = joinBits([
    record ? `Record: ${record}` : '',
    prizeMoney !== '' ? `Prizemoney: ${prizeMoney}` : '',
    firstUp ? `1st Up: ${firstUp}` : '',
    secondUp ? `2nd Up: ${secondUp}` : '',
  ]);

  const records2 = joinBits([
    trackRec ? `Track: ${trackRec}` : '',
    distRec ? `Dist: ${distRec}` : '',
    trackDist ? `Track/Dist: ${trackDist}` : '',
    distanceWins ? `Distance(s) Won: ${distanceWins}` : '',
  ]);

  const records3 = joinBits([
    firmRec ? `Firm: ${firmRec}` : '',
    goodRec ? `Good: ${goodRec}` : '',
    softRec ? `Soft: ${softRec}` : '',
    heavyRec ? `Heavy: ${heavyRec}` : '',
    synthRec ? `Synthetic: ${synthRec}` : '',
  ]);

  return {
    heading,
    meta1,
    meta2,
    meta3,
    records1,
    records2,
    records3,
    colours,
    gear,
  };
}

function RatingSparkline({ runs }: { runs: FormRun[] }) {
  const values = runs
    .map((r) => r.runRating)
    .filter((v): v is number => v !== undefined && Number.isFinite(v))
    .slice(0, 10)
    .reverse();

  if (!values.length) {
    return <div style={styles.emptyMini}>No graph data yet</div>;
  }

  const width = 420;
  const height = 110;
  const pad = 14;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);

  const points = values.map((v, i) => {
    const x = pad + (i * (width - pad * 2)) / Math.max(values.length - 1, 1);
    const y = height - pad - ((v - min) / range) * (height - pad * 2);
    return { x, y, v };
  });

  const line = points.map((p) => `${p.x},${p.y}`).join(' ');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={styles.sparkline}>
      <polyline
        fill="none"
        stroke="#74b9ff"
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={line}
      />
      {points.map((p, idx) => (
        <g key={idx}>
          <circle cx={p.x} cy={p.y} r="4" fill="#ffffff" />
          <text x={p.x} y={p.y - 10} textAnchor="middle" fontSize="10" fill="#dce9f5">
            {p.v.toFixed(1)}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function UpcomingStateMeetingNavigator({
  data,
  formRuns,
  formSummary,
}: {
  data: CsvRow[];
  formRuns: CsvRow[];
  formSummary: CsvRow[];
}) {
  const todayIso = useMemo(() => getTodayIsoLocal(), []);

  const runners = useMemo<RunnerRow[]>(() => {
    return (data || [])
      .map((row) => {
        const raceDate = formatDateKey(firstNonEmpty(row, ['race_date', 'date']));
        const state = firstNonEmpty(row, ['state']).toUpperCase();
        const track = normalizeTrack(firstNonEmpty(row, ['track', 'meeting', 'venue']));
        const raceNo = toNumber(firstNonEmpty(row, ['race_no', 'race_number'])) ?? 0;
        const horse = firstNonEmpty(row, ['horse', 'runner_name', 'name']);
        const horseKey = normalizeHorseKey(firstNonEmpty(row, ['horse_key', 'runner_key', 'horse_id', 'horse']) || horse);
        const horseNo = toNumber(firstNonEmpty(row, ['horse_no', 'runner_no', 'number', 'saddlecloth', 'tab_no']));

        return {
          raceDate,
          state,
          track,
          raceNo,
          horse,
          horseKey,
          horseNo,
          barrier: firstNonEmpty(row, ['barrier', 'bar']),
          jockey: firstNonEmpty(row, ['jockey']),
          trainer: firstNonEmpty(row, ['trainer']),
          ratedPrice: toNumber(firstNonEmpty(row, ['rated_price'])),
          marketPrice: toNumber(firstNonEmpty(row, ['market_price', 'fixed_odds', 'win_odds'])),
          edgePct: toNumber(firstNonEmpty(row, ['edge_pct', 'edge'])),
          silkUrl: firstNonEmpty(row, ['silk_url']),
          scratched: isTruthy(firstNonEmpty(row, ['scratched'])),
          mapComment: firstNonEmpty(row, ['map_comment']),
          speedMapGroup: firstNonEmpty(row, ['speed_map_group']),
          speedMapRank: toNumber(firstNonEmpty(row, ['speed_map_rank'])),
          weight: firstNonEmpty(row, ['weight', 'weight_carried']),
          raw: row,
        };
      })
      .filter((r) => r.raceDate && r.raceDate >= todayIso)
      .filter((r) => r.track && r.horse && r.raceNo > 0)
      .sort((a, b) => {
        if (a.state !== b.state) return STATE_ORDER.indexOf(a.state) - STATE_ORDER.indexOf(b.state);
        if (a.raceDate !== b.raceDate) return a.raceDate.localeCompare(b.raceDate);
        if (a.track !== b.track) return a.track.localeCompare(b.track);
        if (a.raceNo !== b.raceNo) return a.raceNo - b.raceNo;
        const aNo = a.horseNo ?? 9999;
        const bNo = b.horseNo ?? 9999;
        if (aNo !== bNo) return aNo - bNo;
        return a.horse.localeCompare(b.horse);
      });
  }, [data, todayIso]);

  const formSummaryMap = useMemo(() => {
    const map = new Map<string, FormSummary>();

    (formSummary || []).forEach((row) => {
      const horse = firstNonEmpty(row, ['horse', 'runner_name']);
      const horseKey = normalizeHorseKey(firstNonEmpty(row, ['horse_key', 'runner_key', 'horse_id', 'horse']) || horse);
      if (!horseKey) return;

      map.set(horseKey, {
        horseKey,
        horse,
        lastRating: toNumber(firstNonEmpty(row, ['last_run_rating', 'last_rating', 'latest_rating'])),
        avgLast3: toNumber(firstNonEmpty(row, ['last_3_avg_rating', 'avg_last_3', 'average_last_3'])),
        peakRating: toNumber(firstNonEmpty(row, ['best_rating_ever', 'peak_rating', 'best_rating', 'max_run_rating', 'last_10_best_rating'])),
        starts: toNumber(firstNonEmpty(row, ['starts', 'career_starts', 'runs_count_total'])),
        raw: row,
      });
    });

    return map;
  }, [formSummary]);

  const formRunsMap = useMemo(() => {
    const map = new Map<string, FormRun[]>();

    (formRuns || []).forEach((row, idx) => {
      const horse = firstNonEmpty(row, ['horse', 'horse_hist', 'runner_name']);
      const horseKey = normalizeHorseKey(firstNonEmpty(row, ['horse_key', 'runner_key', 'horse_id', 'horse']) || horse);
      if (!horseKey) return;

      const run: FormRun = {
        id: `${horseKey}_${idx}`,
        horseKey,
        horse,
        runDate: firstNonEmpty(row, ['run_date', 'run_date_dt', 'date', 'race_date']),
        track: firstNonEmpty(row, ['track_hist', 'track', 'venue']),
        distance: firstNonEmpty(row, ['distance']),
        raceClass: firstNonEmpty(row, ['race_class', 'class', 'class_name']),
        barrier: firstNonEmpty(row, ['barrier_hist', 'barrier', 'bar']),
        jockey: cleanMaybeMoneyJockey(firstNonEmpty(row, ['jockey_hist', 'jockey'])),
        finishPos: firstNonEmpty(row, ['finish_position', 'finish_pos', 'finish', 'placing', 'position', 'result_text']),
        margin: firstNonEmpty(row, ['margin']),
        sp: firstNonEmpty(row, ['starting_price', 'sp', 'odds']),
        trackCondition: firstNonEmpty(row, ['track_condition', 'going', 'surface_condition']),
        runRating: toNumber(firstNonEmpty(row, ['run_rating', 'rating', 'figure'])),
        raw: row,
      };

      const arr = map.get(horseKey) || [];
      arr.push(run);
      map.set(horseKey, arr);
    });

    map.forEach((runs, key) => {
      map.set(
        key,
        runs
          .slice()
          .sort((a, b) => compareDateDesc(a.runDate, b.runDate))
          .slice(0, 20)
      );
    });

    return map;
  }, [formRuns]);

  const meetings = useMemo<MeetingGroup[]>(() => {
    const map = new Map<string, MeetingGroup>();

    runners.forEach((r) => {
      const key = `${r.state}__${r.raceDate}__${r.track}`;
      const existing = map.get(key);

      if (!existing) {
        map.set(key, {
          key,
          state: r.state,
          raceDate: r.raceDate,
          track: r.track,
          races: [r.raceNo],
        });
      } else if (!existing.races.includes(r.raceNo)) {
        existing.races.push(r.raceNo);
      }
    });

    return Array.from(map.values()).map((m) => ({
      ...m,
      races: m.races.slice().sort((a, b) => a - b),
    }));
  }, [runners]);

  const meetingsByState = useMemo(() => {
    const grouped: Record<string, MeetingGroup[]> = {};
    STATE_ORDER.forEach((state) => {
      grouped[state] = meetings.filter((m) => m.state === state);
    });
    return grouped;
  }, [meetings]);

  const availableStates = useMemo(() => {
    return STATE_ORDER.filter((state) => (meetingsByState[state] || []).length > 0);
  }, [meetingsByState]);

  const [selectedState, setSelectedState] = useState<string>('VIC');
  const [selectedMeetingKey, setSelectedMeetingKey] = useState<string>('');
  const [selectedRaceNo, setSelectedRaceNo] = useState<number>(1);
  const [expandedRunnerKey, setExpandedRunnerKey] = useState<string>('');

  useEffect(() => {
    if (!availableStates.includes(selectedState)) {
      setSelectedState(availableStates[0] || 'VIC');
    }
  }, [availableStates, selectedState]);

  const stateMeetings = meetingsByState[selectedState] || [];

  useEffect(() => {
    if (!stateMeetings.some((m) => m.key === selectedMeetingKey)) {
      const firstMeeting = stateMeetings[0];
      setSelectedMeetingKey(firstMeeting?.key || '');
      setSelectedRaceNo(firstMeeting?.races?.[0] || 1);
      setExpandedRunnerKey('');
    }
  }, [stateMeetings, selectedMeetingKey]);

  const selectedMeeting = stateMeetings.find((m) => m.key === selectedMeetingKey) || null;

  useEffect(() => {
    if (selectedMeeting) {
      if (!selectedMeeting.races.includes(selectedRaceNo)) {
        setSelectedRaceNo(selectedMeeting.races[0] || 1);
      }
      setExpandedRunnerKey('');
    }
  }, [selectedMeeting, selectedRaceNo]);

  const raceRunners = useMemo(() => {
    if (!selectedMeeting) return [];

    return runners
      .filter((r) => r.state === selectedMeeting.state)
      .filter((r) => r.raceDate === selectedMeeting.raceDate)
      .filter((r) => r.track === selectedMeeting.track)
      .filter((r) => r.raceNo === selectedRaceNo)
      .slice()
      .sort((a, b) => {
        if (a.scratched !== b.scratched) return Number(a.scratched) - Number(b.scratched);
        const aNo = a.horseNo ?? 9999;
        const bNo = b.horseNo ?? 9999;
        if (aNo !== bNo) return aNo - bNo;
        return a.horse.localeCompare(b.horse);
      });
  }, [runners, selectedMeeting, selectedRaceNo]);

  return (
    <div style={styles.wrap}>
      <div style={styles.stateTabs}>
        {STATE_ORDER.map((state) => {
          const active = state === selectedState;
          const disabled = !(meetingsByState[state] || []).length;
          return (
            <button
              key={state}
              type="button"
              disabled={disabled}
              onClick={() => setSelectedState(state)}
              style={{
                ...styles.stateTab,
                ...(active ? styles.stateTabActive : {}),
                ...(disabled ? styles.stateTabDisabled : {}),
              }}
            >
              {state}
            </button>
          );
        })}
      </div>

      <div style={styles.layout}>
        <aside style={styles.sidebar}>
          <div style={styles.sidebarTitle}>Meetings</div>

          <div style={styles.meetingList}>
            {stateMeetings.map((meeting) => {
              const active = meeting.key === selectedMeetingKey;
              return (
                <button
                  key={meeting.key}
                  type="button"
                  onClick={() => {
                    setSelectedMeetingKey(meeting.key);
                    setSelectedRaceNo(meeting.races[0] || 1);
                    setExpandedRunnerKey('');
                  }}
                  style={{
                    ...styles.meetingButton,
                    ...(active ? styles.meetingButtonActive : {}),
                  }}
                >
                  <div style={styles.meetingTrack}>{meeting.track}</div>
                  <div style={styles.meetingMeta}>
                    {meeting.raceDate}  {meeting.races.length} races
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <main style={styles.main}>
          {!selectedMeeting ? (
            <div style={styles.emptyBox}>No meeting selected</div>
          ) : (
            <>
              <div style={styles.hero}>
                <div>
                  <div style={styles.heroKicker}>
                    {selectedMeeting.state}  {selectedMeeting.raceDate}
                  </div>
                  <div style={styles.heroTitle}>{selectedMeeting.track}</div>
                </div>

                <div style={styles.raceTabs}>
                  {selectedMeeting.races.map((raceNo) => (
                    <button
                      key={raceNo}
                      type="button"
                      onClick={() => {
                        setSelectedRaceNo(raceNo);
                        setExpandedRunnerKey('');
                      }}
                      style={{
                        ...styles.raceTab,
                        ...(selectedRaceNo === raceNo ? styles.raceTabActive : {}),
                      }}
                    >
                      R{raceNo}
                    </button>
                  ))}
                </div>
              </div>

              <div style={styles.tableHeader}>
                <div>No</div>
                <div>Runner</div>
                <div>Barrier</div>
                <div>Jockey / Trainer</div>
                <div>Rated</div>
                <div>Market</div>
                <div>Edge</div>
              </div>

              <div style={styles.rowsWrap}>
                {raceRunners.map((runner) => {
                  const summary = formSummaryMap.get(runner.horseKey);
                  const runs = formRunsMap.get(runner.horseKey) || [];
                  const rowKey = `${runner.raceDate}_${runner.track}_${runner.raceNo}_${runner.horseKey}`;
                  const expanded = expandedRunnerKey === rowKey;
                  const profile = buildProfileLines(runner, summary);

                  return (
                    <div key={rowKey} style={styles.runnerBlock}>
                      <button
                        type="button"
                        onClick={() => setExpandedRunnerKey(expanded ? '' : rowKey)}
                        style={{
                          ...styles.runnerRowButton,
                          ...(runner.scratched ? styles.runnerRowButtonScratched : {}),
                        }}
                      >
                        <div style={styles.runnerRow}>
                          <div style={styles.runnerNo}>{runner.horseNo ?? ''}</div>

                          <div style={styles.runnerCell}>
                            <div style={styles.runnerIdentity}>
                              {runner.silkUrl ? (
                                <img src={runner.silkUrl} alt="" style={styles.silk} />
                              ) : (
                                <div style={styles.silkFallback}>silks</div>
                              )}

                              <div>
                                <div style={styles.runnerName}>{runner.horse}</div>
                                {runner.scratched ? <div style={styles.scrTag}>SCR</div> : null}
                              </div>
                            </div>
                          </div>

                          <div style={styles.cellText}>{runner.barrier || ''}</div>

                          <div style={styles.jtCell}>
                            <div style={styles.whiteText}>{runner.jockey || ''}</div>
                            <div style={styles.subtle}>{runner.trainer || ''}</div>
                          </div>

                          <div style={styles.cellText}>{formatOdds(runner.ratedPrice)}</div>
                          <div style={styles.cellText}>{formatOdds(runner.marketPrice)}</div>
                          <div style={styles.cellText}>{formatPct(runner.edgePct)}</div>
                        </div>
                      </button>

                      {expanded && (
                        <div style={styles.expandedPanel}>
                          <div style={styles.profileCard}>
                            <div style={styles.profileHeading}>{profile.heading}</div>
                            {profile.meta1 ? <div style={styles.profileLine}>{profile.meta1}</div> : null}
                            {profile.meta2 ? <div style={styles.profileLine}>{profile.meta2}</div> : null}
                            {profile.meta3 ? <div style={styles.profileLine}>{profile.meta3}</div> : null}
                            {profile.colours ? <div style={styles.profileLine}>Colours: {profile.colours}</div> : null}
                            {profile.gear ? <div style={styles.profileLine}>Gear Changes: {profile.gear}</div> : null}
                            {profile.records1 ? <div style={styles.profileLine}>{profile.records1}</div> : null}
                            {profile.records2 ? <div style={styles.profileLine}>{profile.records2}</div> : null}
                            {profile.records3 ? <div style={styles.profileLine}>{profile.records3}</div> : null}
                          </div>

                          <div style={styles.expandedTop}>
                            <div style={styles.card}>
                              <div style={styles.cardTitle}>Runner Summary</div>
                              <div style={styles.statRow}>
                                <span>Last Rating</span>
                                <strong>{formatFigure(summary?.lastRating)}</strong>
                              </div>
                              <div style={styles.statRow}>
                                <span>Average Last 3</span>
                                <strong>{formatFigure(summary?.avgLast3)}</strong>
                              </div>
                              <div style={styles.statRow}>
                                <span>Peak Rating</span>
                                <strong>{formatFigure(summary?.peakRating)}</strong>
                              </div>
                              <div style={styles.statRow}>
                                <span>Starts</span>
                                <strong>{summary?.starts ?? ''}</strong>
                              </div>
                              <div style={styles.statRow}>
                                <span>Weight</span>
                                <strong>{runner.weight || ''}</strong>
                              </div>
                              <div style={styles.statRow}>
                                <span>Map Group</span>
                                <strong>{runner.speedMapGroup || ''}</strong>
                              </div>
                              {runner.mapComment ? <div style={styles.mapComment}>{runner.mapComment}</div> : null}
                            </div>

                            <div style={styles.card}>
                              <div style={styles.cardTitle}>Performance Graph</div>
                              <RatingSparkline runs={runs} />
                              <div style={styles.ratingsRow}>
                                {runs.length ? (
                                  runs
                                    .slice(0, 10)
                                    .map((run) => (
                                      <div key={run.id} style={styles.ratingPill}>
                                        {formatFigure(run.runRating)}
                                      </div>
                                    ))
                                ) : (
                                  <div style={styles.emptyMini}>No recent runs found</div>
                                )}
                              </div>
                            </div>
                          </div>

                          <div style={styles.card}>
                            <div style={styles.cardTitle}>Form Guide</div>

                            <div style={styles.formTableWrap}>
                              <table style={styles.formTable}>
                                <thead>
                                  <tr>
                                    <th>Date</th>
                                    <th>Track</th>
                                    <th>Dist</th>
                                    <th>Class</th>
                                    <th>Barrier</th>
                                    <th>Jockey</th>
                                    <th>Pos</th>
                                    <th>Margin</th>
                                    <th>SP</th>
                                    <th>Cond</th>
                                    <th>Rating</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {runs.length ? (
                                    runs.map((run) => (
                                      <tr key={run.id}>
                                        <td>{run.runDate || ''}</td>
                                        <td>{run.track || ''}</td>
                                        <td>{run.distance || ''}</td>
                                        <td>{run.raceClass || ''}</td>
                                        <td>{run.barrier || ''}</td>
                                        <td>{run.jockey || ''}</td>
                                        <td>{run.finishPos || ''}</td>
                                        <td>{run.margin || ''}</td>
                                        <td>{run.sp || ''}</td>
                                        <td>{run.trackCondition || ''}</td>
                                        <td>{formatFigure(run.runRating)}</td>
                                      </tr>
                                    ))
                                  ) : (
                                    <tr>
                                      <td colSpan={11} style={styles.noFormCell}>
                                        No form runs loaded for this horse.
                                      </td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    width: '100%',
    color: '#edf4fb',
  },
  stateTabs: {
    display: 'flex',
    gap: 10,
    flexWrap: 'wrap',
    marginBottom: 18,
  },
  stateTab: {
    padding: '10px 16px',
    borderRadius: 12,
    border: '1px solid rgba(255,255,255,0.08)',
    background: 'rgba(255,255,255,0.04)',
    color: '#edf4fb',
    cursor: 'pointer',
    fontWeight: 800,
  },
  stateTabActive: {
    background: 'rgba(102, 179, 255, 0.14)',
    borderColor: 'rgba(102, 179, 255, 0.34)',
  },
  stateTabDisabled: {
    opacity: 0.35,
    cursor: 'not-allowed',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '320px 1fr',
    gap: 18,
  },
  sidebar: {
    background: 'rgba(12,18,26,0.96)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 18,
    padding: 16,
  },
  sidebarTitle: {
    fontSize: 13,
    textTransform: 'uppercase',
    letterSpacing: 1.1,
    color: '#8eabc8',
    marginBottom: 12,
    fontWeight: 800,
  },
  meetingList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  meetingButton: {
    textAlign: 'left',
    padding: 14,
    borderRadius: 14,
    border: '1px solid rgba(255,255,255,0.06)',
    background: 'rgba(255,255,255,0.03)',
    color: '#edf4fb',
    cursor: 'pointer',
  },
  meetingButtonActive: {
    background: 'rgba(102, 179, 255, 0.12)',
    borderColor: 'rgba(102, 179, 255, 0.28)',
  },
  meetingTrack: {
    fontWeight: 800,
    marginBottom: 4,
    color: '#ffffff',
  },
  meetingMeta: {
    fontSize: 12,
    color: '#c2d2e2',
  },
  main: {
    background: 'rgba(12,18,26,0.96)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 18,
    padding: 18,
  },
  hero: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 16,
    marginBottom: 18,
  },
  heroKicker: {
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1.1,
    color: '#8eabc8',
    marginBottom: 6,
  },
  heroTitle: {
    fontSize: 34,
    fontWeight: 900,
    lineHeight: 1,
    color: '#ffffff',
  },
  raceTabs: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
  },
  raceTab: {
    padding: '8px 12px',
    borderRadius: 10,
    border: '1px solid rgba(255,255,255,0.08)',
    background: 'rgba(255,255,255,0.04)',
    color: '#edf4fb',
    cursor: 'pointer',
    fontWeight: 800,
  },
  raceTabActive: {
    background: 'rgba(102, 179, 255, 0.14)',
    borderColor: 'rgba(102, 179, 255, 0.34)',
  },
  tableHeader: {
    display: 'grid',
    gridTemplateColumns: '60px 2.3fr 90px 1.6fr 100px 100px 90px',
    gap: 10,
    color: '#c9d9ea',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    padding: '0 10px 8px',
    fontWeight: 800,
  },
  rowsWrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  runnerBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  runnerRowButton: {
    border: 'none',
    padding: 0,
    background: 'transparent',
    textAlign: 'left',
    cursor: 'pointer',
  },
  runnerRowButtonScratched: {
    opacity: 0.58,
  },
  runnerRow: {
    display: 'grid',
    gridTemplateColumns: '60px 2.3fr 90px 1.6fr 100px 100px 90px',
    gap: 10,
    alignItems: 'center',
    padding: '12px 10px',
    borderRadius: 14,
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  runnerNo: {
    color: '#ffffff',
    fontWeight: 900,
  },
  runnerCell: {
    minWidth: 0,
  },
  runnerIdentity: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  silk: {
    width: 30,
    height: 30,
    borderRadius: 8,
    objectFit: 'contain',
    background: '#ffffff',
  },
  silkFallback: {
    width: 30,
    height: 30,
    borderRadius: 8,
    background: 'rgba(255,255,255,0.08)',
    display: 'grid',
    placeItems: 'center',
    fontSize: 8,
    color: '#dce9f5',
    textTransform: 'uppercase',
    fontWeight: 800,
  },
  runnerName: {
    fontWeight: 900,
    color: '#ffffff',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  scrTag: {
    marginTop: 4,
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 900,
    background: 'rgba(255,90,90,0.16)',
    color: '#ffc0c0',
  },
  cellText: {
    fontWeight: 700,
    color: '#ffffff',
  },
  jtCell: {
    minWidth: 0,
    color: '#ffffff',
  },
  whiteText: {
    color: '#ffffff',
    fontWeight: 700,
  },
  subtle: {
    fontSize: 12,
    color: '#d1dfec',
    marginTop: 2,
  },
  expandedPanel: {
    padding: 14,
    borderRadius: 14,
    background: 'rgba(7,11,17,0.96)',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  profileCard: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
  },
  profileHeading: {
    fontSize: 22,
    fontWeight: 900,
    color: '#ffffff',
    marginBottom: 8,
  },
  profileLine: {
    fontSize: 14,
    lineHeight: 1.6,
    color: '#edf4fb',
    marginBottom: 4,
  },
  expandedTop: {
    display: 'grid',
    gridTemplateColumns: '320px 1fr',
    gap: 14,
    marginBottom: 14,
  },
  card: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 14,
    padding: 14,
  },
  cardTitle: {
    fontWeight: 900,
    marginBottom: 12,
    color: '#ffffff',
  },
  statRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '7px 0',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    fontSize: 14,
    color: '#edf4fb',
  },
  mapComment: {
    marginTop: 12,
    fontSize: 13,
    color: '#d1dfec',
    lineHeight: 1.5,
  },
  ratingsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  ratingPill: {
    minWidth: 52,
    textAlign: 'center',
    padding: '8px 10px',
    borderRadius: 10,
    background: 'rgba(255,255,255,0.06)',
    fontWeight: 800,
    color: '#ffffff',
  },
  sparkline: {
    width: '100%',
    height: 120,
    display: 'block',
    background: 'rgba(255,255,255,0.02)',
    borderRadius: 12,
  },
  formTableWrap: {
    overflowX: 'auto',
  },
  formTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
    color: '#edf4fb',
  },
  noFormCell: {
    textAlign: 'center',
    padding: 16,
    color: '#d1dfec',
  },
  emptyBox: {
    minHeight: 400,
    display: 'grid',
    placeItems: 'center',
    color: '#d1dfec',
    fontWeight: 700,
  },
  emptyMini: {
    color: '#d1dfec',
    fontSize: 13,
  },
};


