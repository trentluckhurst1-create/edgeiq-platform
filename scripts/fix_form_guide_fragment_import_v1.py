from pathlib import Path

path = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\RaceFormGuideWorkspace.tsx")

text = path.read_text(encoding="utf-8")

old = 'import { useEffect, useMemo, useState } from "react";'
new = 'import { Fragment, useEffect, useMemo, useState } from "react";'

if old not in text:
    raise SystemExit("FIX_ABORTED: expected React import not found.")

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8", newline="\n")

print("FORM_GUIDE_FRAGMENT_IMPORT_RESTORED_PASS")
