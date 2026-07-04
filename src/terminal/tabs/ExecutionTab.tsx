import React from "react";
import LiveExecutionTerminal from "../../components/LiveExecutionTerminal";

type CsvRow = Record<string, string>;

type ExecutionTabProps = {
  rows: CsvRow[];
};

export default function ExecutionTab({ rows }: ExecutionTabProps): React.ReactElement {
  return (
    <div className="edgeTabSurface">
      <LiveExecutionTerminal rows={rows} />
    </div>
  );
}
