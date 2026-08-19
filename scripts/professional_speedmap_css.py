from pathlib import Path

css = Path(r".\src\edgeiq-speedmap-v2.css")

css.write_text(r'''
/* EDGEIQ SPEED MAP — PROFESSIONAL REBUILD */

.speedmap-v2-shell{
  background:#060b14;
  border:1px solid rgba(51,65,85,.85);
  border-radius:14px;
  padding:10px;
}

.speed-head-title{
  display:flex;
  flex-direction:column;
  gap:2px;
}

.speed-head-title span{
  color:#f8fafc;
  font-size:15px;
  font-weight:800;
  letter-spacing:.06em;
}

.speed-head-title small{
  color:#64748b;
  font-size:10px;
  letter-spacing:.12em;
}

.speed-head-metrics{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
}

.speed-chip{
  min-width:82px;
  background:#0f172a;
  border:1px solid rgba(71,85,105,.8);
  border-radius:8px;
  padding:5px 8px;
}

.speed-chip label{
  display:block;
  color:#64748b;
  font-size:8px;
  font-weight:700;
  letter-spacing:.12em;
}

.speed-chip strong{
  color:#f8fafc;
  font-size:11px;
  font-weight:800;
}

.speedmap-lane-header{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:6px;
  margin-bottom:8px;
}

.speedmap-lane-header div{
  height:26px;
  border-radius:7px;
  background:#111827;
  border:1px solid rgba(71,85,105,.7);
  display:flex;
  align-items:center;
  justify-content:center;
  color:#cbd5e1;
  font-size:9px;
  font-weight:800;
  letter-spacing:.12em;
}

.speedmap-track{
  position:relative;
  height:470px;
  overflow:hidden;
  border-radius:12px;
  border:1px solid rgba(71,85,105,.85);
  background:
    linear-gradient(180deg, rgba(255,255,255,.02), transparent),
    repeating-linear-gradient(
      0deg,
      rgba(148,163,184,.04) 0px,
      rgba(148,163,184,.04) 1px,
      transparent 1px,
      transparent 58px
    ),
    repeating-linear-gradient(
      90deg,
      rgba(148,163,184,.035) 0px,
      rgba(148,163,184,.035) 1px,
      transparent 1px,
      transparent 135px
    ),
    #030712;
}

.speedmap-rail{
  position:absolute;
  left:14px;
  top:14px;
  bottom:14px;
  width:2px;
  background:#94a3b8;
  opacity:.65;
  border-radius:999px;
}

.speedmap-runner{
  position:absolute;
  transform:translate(-50%,-50%);
  width:104px;
  height:26px;
  border-radius:7px;
  background:#131c2b;
  border:1px solid rgba(100,116,139,.65);
  display:flex;
  align-items:center;
  gap:5px;
  padding:3px 5px;
  transition:all .15s ease;
  box-shadow:0 4px 10px rgba(0,0,0,.22);
}

.speedmap-runner:hover{
  transform:translate(-50%,-50%) scale(1.03);
  border-color:#60a5fa;
}

.speedmap-runner.selected{
  background:#172554;
  border-color:#38bdf8;
  box-shadow:0 0 0 1px rgba(56,189,248,.4);
}

.speedmap-runner.leader{
  border-left:3px solid #22c55e;
}

.speedmap-runner.onpace{
  border-left:3px solid #3b82f6;
}

.speedmap-runner.midfield{
  border-left:3px solid #f59e0b;
}

.speedmap-runner.backmarker{
  border-left:3px solid #a855f7;
}

.speedmap-runner img{
  width:14px;
  height:14px;
  border-radius:2px;
  flex:0 0 14px;
}

.speedmap-copy{
  min-width:0;
  flex:1;
}

.speedmap-copy strong{
  display:block;
  color:#f8fafc;
  font-size:7px;
  line-height:1;
  font-weight:800;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}

.speedmap-copy span{
  display:block;
  margin-top:2px;
  color:#94a3b8;
  font-size:6px;
  line-height:1;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}

.speedmap-direction{
  position:absolute;
  top:10px;
  right:12px;
  color:#94a3b8;
  font-size:8px;
  font-weight:800;
  letter-spacing:.12em;
}

.speedmap-rail-label{
  position:absolute;
  left:10px;
  bottom:8px;
  color:#64748b;
  font-size:8px;
  font-weight:800;
  letter-spacing:.14em;
}

.speedmap-wide-label{
  position:absolute;
  right:10px;
  bottom:8px;
  color:#64748b;
  font-size:8px;
  font-weight:800;
  letter-spacing:.14em;
}
''', encoding="utf-8")

print("REBUIILT PROFESSIONAL SPEED MAP CSS")
