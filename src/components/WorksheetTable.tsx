import React from "react";

type Runner = {
  horseNo: number | null;
  horse: string;
  barrier: number | null;
  jockey: string;
  trainer: string;
  ratedPrice: number | null;
  marketPrice: number | null;
  edgePct: number | null;
  is_scratched: number;
};

export default function WorksheetTable({ runners }: { runners: Runner[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr>
          <th>No</th>
          <th>Horse</th>
          <th>Bar</th>
          <th>Jockey</th>
          <th>Trainer</th>
          <th>Rated</th>
          <th>Market</th>
          <th>Edge</th>
        </tr>
      </thead>
      <tbody>
        {runners.map((r, i) => {
          const scr = r.is_scratched === 1;

          return (
            <tr
              key={i}
              className={scr ? "text-red-400 opacity-70 line-through" : ""}
            >
              <td>{r.horseNo}</td>
              <td>
                {r.horse} {scr && <span className="ml-2 text-xs bg-red-600 px-2 py-0.5 rounded">SCR</span>}
              </td>
              <td>{r.barrier}</td>
              <td>{r.jockey}</td>
              <td>{r.trainer}</td>
              <td>{scr ? "-" : r.ratedPrice}</td>
              <td>{scr ? "-" : r.marketPrice}</td>
              <td>{scr ? "-" : r.edgePct}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}



