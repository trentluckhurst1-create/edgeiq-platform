from pathlib import Path

services = Path("src/edgeiq-os/services")
components = Path("src/edgeiq-os/command/components")
css = Path("src/styles/edgeiqProductTerminalV1.css")

services.mkdir(parents=True, exist_ok=True)
components.mkdir(parents=True, exist_ok=True)

(services / "agreement-matrix.ts").write_text(r'''
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

export type AgreementItem = {
  engine: string;
  status: "CONFIRM" | "WATCH" | "NEUTRAL";
};

export type AgreementMatrix = {
  agreement: number;
  items: AgreementItem[];
};

export function buildAgreementMatrix(): AgreementMatrix {

  const pressure = buildPressureEngine();
  const tempo = buildTempoEngine();
  const position = buildPositionEngine();
  const speed = buildSpeedProfile();
  const track = buildTrackSignature();

  const items: AgreementItem[] = [
    {
      engine: "Pressure Engine",
      status: pressure.band === "HIGH" ? "CONFIRM" : "WATCH",
    },
    {
      engine: "Tempo Engine",
      status: tempo.band === "HIGH" ? "CONFIRM" : "WATCH",
    },
    {
      engine: "Position Engine",
      status: position.position ? "CONFIRM" : "NEUTRAL",
    },
    {
      engine: "SpeedProfile",
      status: speed.confidence === "Elite" ? "CONFIRM" : "WATCH",
    },
    {
      engine: "TrackSignature",
      status: "CONFIRM",
    },
  ];

  const confirms = items.filter(x => x.status === "CONFIRM").length;

  return {
    agreement: Math.round(confirms / items.length * 100),
    items,
  };
}
''', encoding="utf-8")

(components / "AgreementMatrix.tsx").write_text(r'''
import { buildAgreementMatrix } from "../../services/agreement-matrix";

export function AgreementMatrix() {

  const matrix = buildAgreementMatrix();

  return (

    <section className="eiq-agreement">

      <header>

        <span>EDGEIQ Intelligence</span>

        <strong>Agreement Matrix</strong>

      </header>

      <div className="eiq-agreement-score">

        {matrix.agreement}%

      </div>

      <div className="eiq-agreement-grid">

        {matrix.items.map(item=>(

          <article key={item.engine}>

            <strong>{item.engine}</strong>

            <span>{item.status}</span>

          </article>

        ))}

      </div>

    </section>

  );

}
''', encoding="utf-8")

with css.open("a",encoding="utf-8") as f:

    f.write(r'''

.eiq-agreement{

margin-top:32px;

padding:32px;

border:1px solid rgba(255,255,255,.08);

border-radius:26px;

background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.015));

}

.eiq-agreement header span{

display:block;

font-size:11px;

letter-spacing:.18em;

text-transform:uppercase;

color:rgba(255,255,255,.45);

}

.eiq-agreement header strong{

display:block;

margin-top:8px;

font-size:32px;

color:#fff;

}

.eiq-agreement-score{

margin-top:28px;

font-size:72px;

font-weight:800;

letter-spacing:-.06em;

color:#fff;

}

.eiq-agreement-grid{

margin-top:30px;

display:grid;

grid-template-columns:repeat(5,minmax(0,1fr));

gap:18px;

}

.eiq-agreement-grid article{

padding:18px;

border-top:1px solid rgba(255,255,255,.08);

}

.eiq-agreement-grid strong{

display:block;

font-size:13px;

color:#fff;

}

.eiq-agreement-grid span{

display:block;

margin-top:8px;

font-size:12px;

color:#8de0aa;

font-weight:700;

letter-spacing:.08em;

}

''')

print("[EDGEIQ] Sprint03A Agreement Matrix built")
