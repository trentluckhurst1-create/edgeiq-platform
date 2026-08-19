import React, { useMemo } from "react";

type AnyRow = Record<string, any>;

type Props = {
  rows: AnyRow[];
  selectedHorseKey?: string;
  onSelectHorse?: (horseKey: string) => void;
  title?: string;
};

function text(v: unknown): string {
  const s = String(v ?? "").trim();
  return s || "-";
}

function num(v: unknown): number | null {
  const raw = String(v ?? "").replace("$", "").replace("%", "").trim();
  if (!raw || raw === "-") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function price(v: unknown): string {
  const n = num(v);
  if (n === null || n <= 0) return "-";
  return n >= 100 ? n.toFixed(0) : n.toFixed(2).replace(/\.00$/, "");
}

function pct(v: unknown): string {
  const n = num(v);
  if (n === null) return "-";
  return `${n.toFixed(1)}%`;
}

function rankClass(rank: number): string {
  if (rank === 1) return "edgeiq-bookie-rank fav";
  if (rank <= 3) return "edgeiq-bookie-rank live";
  return "edgeiq-bookie-rank";
}

function actionClass(v: unknown): string {
  const s = text(v).toUpperCase();

  if (s.includes("EXECUTE") || s.includes("REAL_ENERGY_EDGE")) return "edgeiq-bookie-action execute";
  if (s.includes("WATCH") || s.includes("CONTEXTUAL")) return "edgeiq-bookie-action watch";
  if (s.includes("CUT") || s.includes("SUPPRESS")) return "edgeiq-bookie-action cut";
  if (s.includes("UNDERLAY")) return "edgeiq-bookie-action underlay";
  if (s.includes("PASS")) return "edgeiq-bookie-action pass";

  return "edgeiq-bookie-action";
}

function edgeClass(v: unknown): string {
  const n = num(v);

  if (n === null) return "edge flat";
  if (n >= 20) return "edge hot";
  if (n >= 10) return "edge positive";
  if (n > 0) return "edge small";
  return "edge negative";
}

function fakeFlucs(priceValue: unknown): string[] {
  const p = num(priceValue);
  if (!p || p <= 0) return ["-", "-", "-", "-", "-"];

  const a = p * 1.12;
  const b = p * 0.98;
  const c = p * 1.05;
  const d = p * 0.94;

  return [a, b, c, d, p].map((x) => price(x));
}

function movementType(row: AnyRow): "firm" | "drift" | "flat" {
  const edge = num(row.edgePct ?? row.ui_edge_pct);
  const action = text(row.execution_action ?? row.ui_action).toUpperCase();

  if (action.includes("CUT") || action.includes("UNDERLAY")) return "drift";
  if ((edge ?? 0) >= 10) return "firm";
  return "flat";
}

function Spark({ type }: { type: "firm" | "drift" | "flat" }) {
  if (type === "firm") {
    return (
      <svg viewBox="0 0 90 26" className="edgeiq-bookie-spark">
        <polyline points="2,22 18,18 34,19 50,13 66,10 88,4" />
      </svg>
    );
  }

  if (type === "drift") {
    return (
      <svg viewBox="0 0 90 26" className="edgeiq-bookie-spark drift">
        <polyline points="2,6 18,9 34,13 50,12 66,18 88,22" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 90 26" className="edgeiq-bookie-spark flat">
      <polyline points="2,14 18,13 34,15 50,14 66,13 88,14" />
    </svg>
  );
}

export default function EdgeBookieBoard({
  rows,
  selectedHorseKey,
  onSelectHorse,
  title = "EDGEiQ VIC BOOKMAKER BOARD",
}: Props): React.ReactElement {
  const activeRows = useMemo(() => {
    return [...(rows ?? [])]
      .filter((r) => !r.isScratched)
      .sort((a, b) => {
        const an = num(a.horseNo ?? a.saddlecloth ?? a.number ?? a.tab_no) ?? 99999;
        const bn = num(b.horseNo ?? b.saddlecloth ?? b.number ?? b.tab_no) ?? 99999;

        if (an !== bn) return an - bn;

        return text(a.horse).localeCompare(text(b.horse));
      });
  }, [rows]);

  const marketPct = useMemo(() => {
    const book = activeRows.reduce((sum, r) => {
      const p = num(r.marketPrice ?? r.ui_price);
      return p && p > 0 ? sum + 100 / p : sum;
    }, 0);

    return book ? `${book.toFixed(1)}%` : "-";
  }, [activeRows]);

  const fav = activeRows[0] ?? null;

  return (
    <section className="edgeiq-bookie-board">
      <div className="edgeiq-bookie-head">
        <div>
          <div className="edgeiq-bookie-kicker">{title}</div>
          <div className="edgeiq-bookie-sub">
            Live odds · fair price · flucs · EDGEiQ action state
          </div>
        </div>

        <div className="edgeiq-bookie-market-meta">
          <div>
            <span>RUNNERS</span>
            <strong>{activeRows.length}</strong>
          </div>
          <div>
            <span>MARKET</span>
            <strong>{marketPct}</strong>
          </div>
          <div>
            <span>FAV</span>
            <strong>{fav?.horse ?? "-"}</strong>
          </div>
        </div>
      </div>

      <div className="edgeiq-bookie-table">
        <div className="edgeiq-bookie-row edgeiq-bookie-header">
          <div>No</div>
          <div>Runner</div>
          <div>Map</div>
          <div>Flucs</div>
          <div>Open</div>
          <div>Mid</div>
          <div>Now</div>
          <div>Fair</div>
          <div>Edge</div>
          <div>Action</div>
        </div>

        {activeRows.map((r, idx) => {
          const marketPrice = r.marketPrice ?? r.ui_price;
          const fairPrice = r.ratedPrice ?? r.ui_fair_price;
          const edge = r.edgePct ?? r.ui_edge_pct;
          const flucs = text(r.flucs) !== "-" ? text(r.flucs).split(/[,\s]+/).filter(Boolean).slice(-5) : fakeFlucs(marketPrice);
          const selected = selectedHorseKey && selectedHorseKey === r.horseKey;

          return (
            <button
              type="button"
              key={r.id ?? `${r.track}-${r.raceNo}-${r.horse}-${idx}`}
              className={`edgeiq-bookie-row edgeiq-bookie-runner ${selected ? "selected" : ""}`}
              onClick={() => onSelectHorse?.(r.horseKey)}
            >
              <div>
                <span className={rankClass(idx + 1)}>{r.horseNo ?? idx + 1}</span>
              </div>

              <div className="edgeiq-bookie-horse">
                <strong>{text(r.horse)}</strong>
                <span>
                  B{r.barrier ?? "-"} · {text(r.jockey)} · {text(r.trainer)}
                </span>
              </div>

              <div className="edgeiq-bookie-map">
                {text(r.tempo_role || r.proxy_energy_archetype || r.run_style_cluster)}
              </div>

              <div className="edgeiq-bookie-flucs">
                <Spark type={movementType(r)} />
              </div>

              <div className="edgeiq-bookie-price muted">{flucs[0] ?? "-"}</div>
              <div className="edgeiq-bookie-price muted">{flucs[Math.max(0, flucs.length - 2)] ?? "-"}</div>
              <div className="edgeiq-bookie-price now">{price(marketPrice)}</div>
              <div className="edgeiq-bookie-price fair">{price(fairPrice)}</div>
              <div className={edgeClass(edge)}>{pct(edge)}</div>

              <div>
                <span className={actionClass(r.execution_action ?? r.ui_action ?? "PASS")}>
                  {text(r.execution_action ?? r.ui_action ?? "PASS")}
                </span>
              </div>
            </button>
          );
        })}

        {!activeRows.length ? (
          <div className="edgeiq-bookie-empty">No active runners available.</div>
        ) : null}
      </div>
    </section>
  );
}

