from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx"
text = path.read_text(encoding="utf-8")
text = text.replace('import { useMemo, useState } from "react";', 'import { Fragment, useMemo, useState } from "react";')
text = text.replace("                <>", '                <Fragment key={runner.key}>', 1)
text = text.replace("                </>", "                </Fragment>", 1)
path.write_text(text, encoding="utf-8", newline="\n")
