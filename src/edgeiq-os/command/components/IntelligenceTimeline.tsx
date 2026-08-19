
import { CommandService } from "../../services/CommandService";

export function IntelligenceTimeline(){

const timeline = CommandService.buildIntelligenceTimeline();

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
