import React from "react";
import WorksheetTable from "./WorksheetTable";

export default function Worksheet({ runners }: any) {
  const rows = runners.map((r: any) => ({
    horseNo: r.horseNo,
    horse: r.horse,
    barrier: r.barrier,
    jockey: r.jockey,
    trainer: r.trainer,
    ratedPrice: r.ratedPrice,
    marketPrice: r.marketPrice,
    edgePct: r.edgePct,
    is_scratched: Number(r.is_scratched ?? 0),
  }));

  rows.sort((a: any, b: any) => {
    if (a.is_scratched !== b.is_scratched) {
      return a.is_scratched - b.is_scratched;
    }
    return (a.horseNo ?? 99) - (b.horseNo ?? 99);
  });

  return <WorksheetTable runners={rows} />;
}

