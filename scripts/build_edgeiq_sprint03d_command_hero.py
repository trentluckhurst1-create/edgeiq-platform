from pathlib import Path
import re

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

text = workspace.read_text(encoding="utf-8")

# -------------------------------------------------------------
# Imports
# -------------------------------------------------------------

imports = '''

import { ConfidenceProfile } from "./components/ConfidenceProfile";
import { AgreementMatrix } from "./components/AgreementMatrix";
import { IntelligenceTimeline } from "./components/IntelligenceTimeline";

'''

if "AgreementMatrix" not in text:
    text = re.sub(
        r'(import\s+\{.*?DecisionTimeline.*?;\n)',
        r'\1' + imports,
        text,
        count=1,
        flags=re.S,
    )

# -------------------------------------------------------------
# COMMAND HERO
# -------------------------------------------------------------

hero = '''

<section className="eiq-command-hero">

<div className="eiq-command-left">

<div className="eiq-command-label">

EDGEIQ COMMAND

</div>

<h1>

Operational Assessment

</h1>

<h2>

MONITOR

</h2>

<p>

Pressure is expected to increase through the first section of the race.
Current intelligence engines remain in strong agreement.
Continue monitoring market behaviour before final assessment.

</p>

<div className="eiq-command-watchlist">

<div>

<strong>WATCH</strong>

<span>Late Market Support</span>

</div>

<div>

<strong>WATCH</strong>

<span>Track Downgrade</span>

</div>

<div>

<strong>WATCH</strong>

<span>Early Speed Pressure</span>

</div>

</div>

</div>

<div className="eiq-command-right">

<ConfidenceProfile />

</div>

</section>

<section className="eiq-command-two-column">

<div>

<AgreementMatrix />

</div>

<div>

<IntelligenceTimeline />

</div>

</section>

'''

marker = "<AssessmentJourney"

if marker in text and "eiq-command-hero" not in text:

    text = text.replace(
        marker,
        hero + "\n\n" + marker,
        1,
    )

workspace.write_text(text,encoding="utf-8")

# -------------------------------------------------------------
# CSS
# -------------------------------------------------------------

with css.open("a",encoding="utf-8") as f:

    f.write(r'''

/* ===========================================================
COMMAND HERO V1
=========================================================== */

.eiq-command-hero{

display:grid;

grid-template-columns:1.2fr .9fr;

gap:36px;

margin-bottom:42px;

align-items:start;

}

.eiq-command-left{

padding:38px;

border-radius:30px;

border:1px solid rgba(255,255,255,.08);

background:

radial-gradient(circle at top left,rgba(126,220,155,.08),transparent 34%),

linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.015));

}

.eiq-command-label{

font-size:11px;

letter-spacing:.22em;

text-transform:uppercase;

color:rgba(255,255,255,.45);

font-weight:800;

}

.eiq-command-left h1{

margin-top:12px;

font-size:52px;

line-height:.95;

letter-spacing:-.07em;

color:#f6f3ea;

}

.eiq-command-left h2{

margin-top:18px;

font-size:18px;

letter-spacing:.18em;

text-transform:uppercase;

color:#7edc9b;

}

.eiq-command-left p{

margin-top:24px;

max-width:760px;

line-height:1.75;

font-size:15px;

color:rgba(255,255,255,.70);

}

.eiq-command-watchlist{

display:grid;

grid-template-columns:repeat(3,1fr);

gap:18px;

margin-top:34px;

}

.eiq-command-watchlist div{

padding:18px;

border-top:1px solid rgba(255,255,255,.08);

}

.eiq-command-watchlist strong{

display:block;

font-size:11px;

letter-spacing:.18em;

text-transform:uppercase;

color:#7edc9b;

}

.eiq-command-watchlist span{

display:block;

margin-top:10px;

font-size:15px;

color:#fff;

}

.eiq-command-two-column{

display:grid;

grid-template-columns:1fr 1fr;

gap:30px;

margin-top:30px;

}

@media(max-width:1200px){

.eiq-command-hero{

grid-template-columns:1fr;

}

.eiq-command-two-column{

grid-template-columns:1fr;

}

}

''')

print("[EDGEIQ] Sprint03D COMMAND Hero redesign built")
