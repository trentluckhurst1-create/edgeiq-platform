from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''.racenet-band-fill {
  position: absolute;
  top: 6px;
  bottom: 6px;
  left: 0;
  right: 0;
  background: #c6ccd2;
}''',
'''.racenet-band-fill {
  position: absolute;
  top: 6px;
  bottom: 6px;
  right: 0;
  background: #c6ccd2;
}'''
)

text = text.replace(
'''  max-width: 350px;
  min-width: 205px;
  height: 28px;
  transform: translateY(-50%);''',
'''  max-width: 390px;
  min-width: 250px;
  height: 30px;
  transform: translateY(-50%);'''
)

text = text.replace(
'''  background: transparent;
  color: #1f2937;''',
'''  background: rgba(246, 248, 250, 0.92);
  color: #1f2937;'''
)

text = text.replace(
'''  font-size: 13px;
  font-weight: 950;''',
'''  font-size: 13px;
  font-weight: 950;'''
)

text = text.replace(
'''  max-width: 190px;''',
'''  max-width: 230px;'''
)

text = text.replace(
'''  border-radius: 999px;
  background: #2b2928;''',
'''  border-radius: 999px;
  background: #2b2928;'''
)

text += r'''

/* RIGHT-ANCHORED RACENET BARRIER MAP FIX */
.racenet-horse-marker {
  left: auto !important;
  justify-content: flex-start;
}

.racenet-band-fill {
  border-radius: 999px 0 0 999px;
  opacity: .92;
}

.racenet-band-fill.on-pace {
  background: linear-gradient(90deg, rgba(185, 215, 169, 0.18), #b9d7a9);
}

.racenet-band-fill.midfield {
  background: linear-gradient(90deg, rgba(191, 197, 203, 0.22), #bfc5cb);
}

.racenet-band-fill.backmarker {
  background: linear-gradient(90deg, rgba(234, 215, 162, 0.22), #ead7a2);
}

.racenet-band-fill.unknown {
  background: linear-gradient(90deg, rgba(201, 167, 245, 0.22), #c9a7f5);
}

.racenet-horse-marker.selected {
  background: rgba(236, 253, 245, 0.98);
}

.racenet-horse-marker.selected::before {
  content: "";
  position: absolute;
  inset: -4px;
  border: 2px solid rgba(16, 185, 129, 0.95);
  border-radius: 999px;
  pointer-events: none;
}

.racenet-barrier-row {
  overflow: hidden;
}

.racenet-barrier-no {
  z-index: 20;
}
'''

path.write_text(text, encoding="utf-8")
print("RIGHT BARRIER ANCHOR CSS FIX APPLIED")
