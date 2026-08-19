type Row = Record<string, any>;

type CareerHistoryModalProps = {
  fullHistoryRunner: any;
  setFullHistoryRunner: any;
  firstNum: any;
  historyFinishText: any;
  historyRatingValue: any;
  horse: any;
  firstText: any;
  renderMetricValue: any;
  historyRunKey: any;
  formatHistoryDate: any;
  historyDateText: any;
  historyTrackText: any;
  historyDistanceText: any;
  historyClassText: any;
  historyGoingText: any;
  historyJockeyText: any;
  historySpText: any;
  ratedHistoryRows: any;
};

export function CareerHistoryModal({
  fullHistoryRunner,
  setFullHistoryRunner,
  firstNum,
  historyFinishText,
  historyRatingValue,
  horse,
  firstText,
  renderMetricValue,
  historyRunKey,
  formatHistoryDate,
  historyDateText,
  historyTrackText,
  historyDistanceText,
  historyClassText,
  historyGoingText,
  historyJockeyText,
  historySpText,
  ratedHistoryRows,
}: CareerHistoryModalProps) {
  if (!fullHistoryRunner) return null;

const modalRows = fullHistoryRunner.runnerHistory || [];
 const ratedRows = ratedHistoryRows(modalRows);
 const career = fullHistoryRunner.runnerCareer || {};
 const starts = firstNum(career, ["career_starts", "starts"]) ?? modalRows.length;
 const wins = firstNum(career, ["career_wins", "wins"]) ?? modalRows.filter((run) => Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, "")) === 1).length;
 const places = firstNum(career, ["career_places", "places"]) ?? modalRows.filter((run) => { const pos = Number(String(historyFinishText(run)).replace(/[^0-9.-]/g, "")); return Number.isFinite(pos) && pos > 0 && pos <= 3; }).length;
 const winRate = firstNum(career, ["career_win_pct", "win_pct"]) ?? (starts ? (wins / starts) * 100 : null);
 const placeRate = firstNum(career, ["career_place_pct", "place_pct"]) ?? (starts ? (places / starts) * 100 : null);
 const peak = ratedRows.length ? Math.max(...ratedRows.map((run) => historyRatingValue(run) ?? Number.NEGATIVE_INFINITY).filter((value) => Number.isFinite(value))) : null;
 const avg = ratedRows.length ? ratedRows.reduce((sum, run) => sum + (historyRatingValue(run) ?? 0), 0) / ratedRows.length : null;
 const cleanHistory = (value: unknown) => {
 const raw = String(value ?? "").trim();
 if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE GAP|SOURCE_MISSING|NULL|N\/A|NA|UNDEFINED|0\.0)$/i.test(raw)) return "-";
 return raw;
 };
 return <div className="edgeiq-career-modal-backdrop" role="dialog" aria-modal="true" aria-label="Full career history"><section className="edgeiq-career-modal"><header><div><span>Full Career History</span><strong>{horse(fullHistoryRunner.row)}</strong><em>{firstText(fullHistoryRunner.row, ["trainer", "trainer_name"], "-")} / {firstText(fullHistoryRunner.row, ["jockey", "jockey_name", "rider"], "-")}</em></div><button type="button" onClick={() => setFullHistoryRunner(null)} aria-label="Close full career history">Close</button></header><div className="edgeiq-career-summary">{[["Starts", starts], ["Wins", wins], ["Places", places], ["Win %", winRate], ["Place %", placeRate], ["Peak EPI", peak], ["Average EPI", avg]].map(([label, value]) => <article key={`career-summary-${label}`}><span>{label}</span><strong>{typeof value === "number" ? (String(label).includes("%") ? `${value.toFixed(1)}%` : renderMetricValue(value, 1)) : "-"}</strong></article>)}</div><div className="edgeiq-career-history-table" role="table" aria-label="Runner full career history"><div className="edgeiq-career-history-row head" role="row">{['DATE','TRACK','DIST','CLASS','GOING','BAR','JOCKEY','POS','MARGIN','SP','EPI','SETTLED / RUN STYLE'].map((label) => <span key={`career-head-${label}`}>{label}</span>)}</div>{modalRows.length ? modalRows.map((run, index) => <div className="edgeiq-career-history-row" role="row" key={`career-history-${index}-${historyRunKey(run)}`}><span>{cleanHistory(formatHistoryDate(historyDateText(run)))}</span><span>{cleanHistory(historyTrackText(run))}</span><span>{cleanHistory(historyDistanceText(run))}</span><span>{cleanHistory(historyClassText(run))}</span><span>{cleanHistory(historyGoingText(run))}</span><span>{cleanHistory(firstText(run, ["barrier", "draw", "barrier_number"], ""))}</span><span>{cleanHistory(historyJockeyText(run))}</span><span>{cleanHistory(historyFinishText(run))}</span><span>{cleanHistory(firstText(run, ["margin", "beaten_margin"], ""))}</span><span>{cleanHistory(historySpText(run))}</span><span>{historyRatingValue(run) === null ? "-" : renderMetricValue(historyRatingValue(run), 1)}</span><span>{cleanHistory(firstText(run, ["settling_position", "run_style", "pos_800", "pos_400"], ""))}</span></div>) : <div className="edgeiq-career-history-empty">Career history not loaded for this runner.</div>}</div></section></div>;
}


