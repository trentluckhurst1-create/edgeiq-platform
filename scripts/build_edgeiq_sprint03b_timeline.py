from pathlib import Path

services = Path("src/edgeiq-os/services")
components = Path("src/edgeiq-os/command/components")
css = Path("src/styles/edgeiqProductTerminalV1.css")

services.mkdir(parents=True, exist_ok=True)
components.mkdir(parents=True, exist_ok=True)

(services / "intelligence-timeline.ts").write_text(r'''
import { buildAgreementMatrix } from "./agreement-matrix";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildTrackSignature } from "./track-signature";

export type TimelineEvent = {
  time: string;
  title: string;
  impact: "HIGH" | "MEDIUM" | "LOW";
  narrative: string;
};

export type IntelligenceTimeline = {
  overallAgreement: number;
  events: TimelineEvent[];
};

export function buildIntelligenceTimeline(): IntelligenceTimeline {

  const agreement = buildAgreementMatrix();
  const pressure = buildPressureEngine();
  const tempo = buildTempoEngine();
  const track = buildTrackSignature();

  return {

    overallAgreement: agreement.agreement,

    events: [

      {
        time: "08:30",
        title: "TrackSignature Updated",
        impact: "MEDIUM",
        narrative: track.assessment,
      },

      {
        time: "08:47",
        title: "Pressure Engine",
        impact: pressure.band === "HIGH" ? "HIGH" : "MEDIUM",
        narrative: pressure.summary,
      },

      {
        time: "09:05",
        title: "Tempo Engine",
        impact: "MEDIUM",
        narrative: tempo.raceRead,
      },

      {
        time: "09:24",
        title: "RaceFlow Revised",
        impact: "HIGH",
        narrative: pressure.tacticalRead,
      },

      {
        time: "09:41",
        title: "Operational Assessment",
        impact: "HIGH",
        narrative:
          "EDGEiQ intelligence engines have reached operational agreement.",
      },

    ],
  };

}
''',encoding="utf-8")

(components / "IntelligenceTimeline.tsx").write_text(r'''
import { buildIntelligenceTimeline } from "../../services/intelligence-timeline";

export function IntelligenceTimeline(){

const timeline = buildIntelligenceTimeline();

return(

<section className="eiq-timeline">

<header>

<span>EDGEIQ Intelligence</span>

<strong>Operational Timeline</strong>

<b>{timeline.overallAgreement}% Agreement</b>

</header>

<div className="eiq-timeline-list">

{timeline.events.map(event=>(

<article key={event.time}>

<div className="eiq-timeline-time">

{event.time}

</div>

<div className="eiq-timeline-node">

<div className={`eiq-impact eiq-impact-${event.impact.toLowerCase()}`} />

</div>

<div className="eiq-timeline-body">

<strong>{event.title}</strong>

<small>{event.impact} IMPACT</small>

<p>{event.narrative}</p>

</div>

</article>

))}

</div>

</section>

);

}
''',encoding="utf-8")

with css.open("a",encoding="utf-8") as f:

    f.write(r'''

.eiq-timeline{

margin-top:42px;

padding:34px;

border-radius:28px;

background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.015));

border:1px solid rgba(255,255,255,.08);

}

.eiq-timeline header span{

display:block;

font-size:11px;

letter-spacing:.18em;

text-transform:uppercase;

color:rgba(255,255,255,.42);

}

.eiq-timeline header strong{

display:block;

margin-top:8px;

font-size:34px;

color:#fff;

letter-spacing:-.05em;

}

.eiq-timeline header b{

display:block;

margin-top:12px;

font-size:18px;

color:#8de0aa;

}

.eiq-timeline-list{

margin-top:34px;

display:flex;

flex-direction:column;

gap:22px;

}

.eiq-timeline-list article{

display:grid;

grid-template-columns:90px 26px 1fr;

gap:22px;

align-items:flex-start;

}

.eiq-timeline-time{

font-size:14px;

font-weight:700;

color:#f6f3ea;

opacity:.75;

}

.eiq-timeline-node{

display:flex;

justify-content:center;

position:relative;

min-height:100%;

}

.eiq-timeline-node:after{

content:"";

position:absolute;

top:18px;

bottom:-26px;

width:2px;

background:rgba(255,255,255,.08);

}

.eiq-timeline-list article:last-child .eiq-timeline-node:after{

display:none;

}

.eiq-impact{

width:14px;

height:14px;

border-radius:999px;

margin-top:2px;

}

.eiq-impact-high{

background:#ff6b6b;

}

.eiq-impact-medium{

background:#f4c542;

}

.eiq-impact-low{

background:#71d99e;

}

.eiq-timeline-body strong{

display:block;

font-size:18px;

color:#fff;

}

.eiq-timeline-body small{

display:block;

margin-top:4px;

font-size:11px;

letter-spacing:.15em;

color:#8de0aa;

}

.eiq-timeline-body p{

margin-top:10px;

font-size:13px;

line-height:1.65;

color:rgba(255,255,255,.66);

max-width:780px;

}

''')

print("[EDGEIQ] Sprint03B Intelligence Timeline built")
