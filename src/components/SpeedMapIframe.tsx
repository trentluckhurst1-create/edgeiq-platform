import React from "react";

type Runner = {
  horse: string;
  horse_no: number;
  barrier: number;
  map_group: string;
  map_color: string;
  map_start_x: number;
  map_end_x: number;
};

type Props = {
  data: Runner[];
};

const zones = [
  { label: "BACKMARKER", left: 0, width: 25 },
  { label: "MIDFIELD", left: 25, width: 25 },
  { label: "ON PACE", left: 50, width: 25 },
  { label: "LEADER", left: 75, width: 25 },
];

export default function SpeedMapTab({ data }: Props) {
  if (!data || data.length === 0) {
    return <div style={{ padding: 20 }}>No speed map data</div>;
  }

  return (
    <div style={{ padding: 20, background: "#0b0b0b", color: "#fff" }}>
      
      {/* ZONE HEADER */}
      <div style={{ position: "relative", height: 40, marginBottom: 20 }}>
        {zones.map((z) => (
          <div
            key={z.label}
            style={{
              position: "absolute",
              left: `${z.left}%`,
              width: `${z.width}%`,
              textAlign: "center",
              fontSize: 12,
              color: "#aaa",
            }}
          >
            {z.label}
          </div>
        ))}
      </div>

      {/* RUNNERS */}
      {data
        .sort((a, b) => (a.barrier || 99) - (b.barrier || 99))
        .map((r, i) => {
          const width = r.map_end_x - r.map_start_x;

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              {/* LEFT INFO */}
              <div style={{ width: 220 }}>
                <b>B{r.barrier}</b> #{r.horse_no} {r.horse}
              </div>

              {/* MAP BAR */}
              <div style={{ flex: 1, position: "relative", height: 22 }}>
                <div
                  style={{
                    position: "absolute",
                    left: `${r.map_start_x}%`,
                    width: `${width}%`,
                    height: "100%",
                    background: r.map_color,
                    borderRadius: 4,
                  }}
                />
              </div>
            </div>
          );
        })}
    </div>
  );
}


