from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''  background: #f5f5f4;''',
'''  background:
    linear-gradient(180deg, rgba(5, 16, 24, 0.98), rgba(2, 8, 14, 0.99));'''
)

text = text.replace(
'''  color: #1f2937;''',
'''  color: #dbeafe;'''
)

text = text.replace(
'''  background: #c6ccd2;''',
'''  background: rgba(148, 163, 184, 0.28);'''
)

text = text.replace(
'''  background: #b9d7a9;''',
'''  background: rgba(34, 197, 94, 0.86);'''
)

text = text.replace(
'''  background: #bfc5cb;''',
'''  background: rgba(234, 179, 8, 0.86);'''
)

text = text.replace(
'''  background: #ead7a2;''',
'''  background: rgba(239, 68, 68, 0.86);'''
)

text = text.replace(
'''  background: #c9a7f5;''',
'''  background: rgba(148, 163, 184, 0.38);'''
)

text = text.replace(
'''  background: #ececec;''',
'''  background: rgba(15, 23, 42, 0.42);'''
)

text = text.replace(
'''  background: rgba(246, 248, 250, 0.92);
  color: #1f2937;''',
'''  background: rgba(3, 10, 18, 0.96);
  color: #e5f2ff;
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.28);'''
)

text = text.replace(
'''  color: #374151;''',
'''  color: #e5f2ff;'''
)

text = text.replace(
'''  color: #4b5563;''',
'''  color: #dbeafe;'''
)

text = text.replace(
'''  background: #ffffff;
  border: 1px solid #d1d5db;''',
'''  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(148, 163, 184, 0.34);'''
)

text = text.replace(
'''  background: #2b2928;''',
'''  background: rgba(15, 23, 42, 0.95);'''
)

text = text.replace(
'''  color: #ffffff;''',
'''  color: #ffffff;'''
)

text = text.replace(
'''  border-top: 1px solid rgba(120, 113, 108, 0.35);
  color: #374151;''',
'''  border-top: 1px solid rgba(148, 163, 184, 0.16);
  color: #cbd5e1;'''
)

text += r'''

/* EDGEIQ DARK ANCHORED BARRIER MAP FINAL PASS */
.racenet-barrier-row {
  border-bottom: 1px solid rgba(148, 163, 184, 0.10);
  background: rgba(2, 8, 16, 0.72);
}

.racenet-band-fill {
  right: 34px !important;
  left: auto !important;
  border-radius: 999px 0 0 999px;
  opacity: .88;
  box-shadow: 0 0 18px rgba(0, 0, 0, 0.18);
}

.racenet-band-fill.on-pace {
  background: linear-gradient(90deg, rgba(34, 197, 94, 0.10), rgba(34, 197, 94, 0.82));
}

.racenet-band-fill.midfield {
  background: linear-gradient(90deg, rgba(234, 179, 8, 0.10), rgba(234, 179, 8, 0.82));
}

.racenet-band-fill.backmarker {
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.10), rgba(239, 68, 68, 0.82));
}

.racenet-horse-marker {
  background: rgba(3, 10, 18, 0.97) !important;
  color: #f8fafc !important;
}

.racenet-horse-marker strong {
  color: #f8fafc !important;
}

.racenet-horse-marker.selected {
  background: rgba(4, 18, 16, 0.98) !important;
}

.racenet-legend .legend-pace {
  background: rgba(34, 197, 94, 0.86);
}

.racenet-legend .legend-mid {
  background: rgba(234, 179, 8, 0.86);
}

.racenet-legend .legend-back {
  background: rgba(239, 68, 68, 0.86);
}

.racenet-map-grid {
  opacity: .25;
}
'''

path.write_text(text, encoding="utf-8")
print("ANCHORED STRIP DARK CSS FIX APPLIED")
