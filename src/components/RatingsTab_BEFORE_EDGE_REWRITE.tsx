import React from "react";
import type { CareerStats, FormHistoryRow, RatingDisplayRow } from "../App";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  historyByHorse: Map<string, FormHistoryRow[]>;
  careerStats?: CareerStats | null;
};

function rating(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return value.toFixed(1);
}

function price(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value) || value <= 0) return "-";
  return value.toFixed(2);
}

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return `${Math.max(-99.9, Math.min(999.9, value)).toFixed(1)}%`;
}

function silk(url?: string): string {
  return url || "/silks/default.svg";
}




function edgeTone(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "edgeiq-muted";
  if (v >= 20) return "edgeiq-green";
  if (v > 0) return "edgeiq-lime";
  return "edgeiq-red";
}

function sortedRows(rows: RatingDisplayRow[]): RatingDisplayRow[] {
  const seen = new Set<string>();
  const unique = rows.filter((r) => {
    const key = `${r.raceDate}|${r.track}|${r.raceNo}|${r.horseNo}|${r.horseKey}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return unique.sort((a, b) => {
    if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
    return (a.horseNo ?? 999) - (b.horseNo ?? 999);
  });
}

export default function RatingsTab({
  runners,
  selectedHorseKey,
  onSelectHorse,
}: Props): React.ReactElement {
  const rows = sortedRows(runners);
  const selected = rows.find((row) => row.horseKey === selectedHorseKey) ?? rows[0] ?? null;

  return (
    <section className="edgeiq-ratings">
      <div className="edgeiq-ratings-card">
        <table className="edgeiq-ratings-table">
          <colgroup>
            <col className="col-rank" />
            <col className="col-runner" />
            <col className="col-num" />
            <col className="col-num" />
            <col className="col-num" />
            <col className="col-num" />
            <col className="col-num" />
            <col className="col-num" />
            <col className="col-num" />
            <col className="col-edge" />
          </colgroup>

          <thead>
            <tr>
              <th>Saddlecloth</th>
              <th>Runner</th>
              <th>Today</th>
              <th>LS1</th>
              <th>LS2</th>
              <th>LS3</th>
              <th>Peak</th>
              <th>Rated</th>
              <th>Market</th>
              <th>Edge</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => {
              const active = selected?.horseKey === row.horseKey;

              return (
                <tr
                  key={row.id}
                  onClick={() => !row.isScratched && onSelectHorse(row.horseKey)}
                  className={`${active ? "selected is-selected" : ""} ${row.isScratched ? "scratched is-scratched" : ""}`}
                >
                  <td className="num">{row.horseNo ?? "-"}</td>

                  <td>
                    <div className="edgeiq-rating-runner">
                      <img
                        src={silk(row.silkUrl)}
                        alt=""
                        onError={(e) => {
                          e.currentTarget.onerror = null;
                          e.currentTarget.src = "/silks/default.svg";
                        }}
                      />
                      <strong>{row.horse}</strong>
                    </div>
                  </td>

                  <td className={"num"}>{rating(row.todayRating)}</td>
                  <td className={"num"}>{rating(row.ls1)}</td>
                  <td className={"num"}>{rating(row.ls2)}</td>
                  <td className={"num"}>{rating(row.ls3)}</td>
                  <td className={"num"}>{rating(row.peak)}</td>
                  <td className="num">{price(row.ratedPrice)}</td>
                  <td className="num">{row.isScratched ? "SCR" : price(row.marketPrice)}</td>
                  <td className={`num strong ${edgeTone(row.edgePct)}`}>{pct(row.edgePct)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selected ? (
        <div className="edgeiq-ratings-detail">
          <div className="edgeiq-rating-runner">
            <img
              src={silk(selected.silkUrl)}
              alt=""
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = "/silks/default.svg";
              }}
            />
            <strong>{selected.horse}</strong>
          </div>

          <div className="edgeiq-rating-metrics">
            <div><span>Saddlecloth</span><strong>{selected.horseNo ?? "-"}</strong></div>
            <div><span>Today</span><strong>{rating(selected.todayRating)}</strong></div>
            <div><span>Rated</span><strong>{price(selected.ratedPrice)}</strong></div>
            <div><span>Market</span><strong>{selected.isScratched ? "SCR" : price(selected.marketPrice)}</strong></div>
            <div><span>Edge</span><strong className={edgeTone(selected.edgePct)}>{pct(selected.edgePct)}</strong></div>
            <div><span>Peak</span><strong>{rating(selected.peak)}</strong></div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

