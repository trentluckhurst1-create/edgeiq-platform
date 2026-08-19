from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text += r'''

/* FOUR-ZONE SCATTER MAP OVERRIDE */
.speedmap-track{
  height:520px !important;
}

.speedmap-runner{
  width:92px !important;
  height:24px !important;
  padding:3px 5px !important;
  border-radius:7px !important;
}

.speedmap-runner img{
  width:13px !important;
  height:13px !important;
  flex:0 0 13px !important;
}

.speedmap-copy strong{
  font-size:6.8px !important;
  max-width:58px !important;
}

.speedmap-copy span{
  font-size:5.8px !important;
  max-width:58px !important;
}

.speedmap-track::before{
  content:"FRONT";
  position:absolute;
  left:14px;
  top:10px;
  color:#94a3b8;
  font-size:9px;
  font-weight:900;
  letter-spacing:.16em;
}

.speedmap-track::after{
  content:"REAR";
  position:absolute;
  left:14px;
  bottom:10px;
  color:#64748b;
  font-size:9px;
  font-weight:900;
  letter-spacing:.16em;
}
'''

path.write_text(text, encoding="utf-8")
print("PATCHED FOUR-ZONE SCATTER CSS")
