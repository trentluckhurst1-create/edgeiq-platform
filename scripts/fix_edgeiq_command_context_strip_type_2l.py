from pathlib import Path

path = Path("src/services/buildCommandExecutiveSummary.ts")
text = path.read_text(encoding="utf-8")

if "raceContextStrip?: string[];" not in text:
    text = text.replace(
'''  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };
};''',
'''  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };
  raceContextStrip?: string[];
};'''
    )

path.write_text(text, encoding="utf-8")
print("[EDGEIQ_COMMAND_2L_FIX] service summary type updated")
