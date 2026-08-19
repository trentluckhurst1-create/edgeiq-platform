from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
text = path.read_text(encoding="utf-8")
text = text.replace(
    "  type FormGuideProfileGroup,\n  type FormGuideRunnerDisplay,\n} from \"../services/formGuideNormaliser\";",
    "  type FormGuideRunnerDisplay,\n} from \"../services/formGuideNormaliser\";",
)
text = text.replace(
    "import { buildRunnerProfileDossier } from \"../services/formGuideWorkspaceViewModel\";",
    "import { buildRunnerProfileDossier, type FormGuideProfileGroup } from \"../services/formGuideWorkspaceViewModel\";",
)
path.write_text(text, encoding="utf-8", newline="\n")
print("EDGEIQ_FORM_GUIDE_FINAL_SPEC_IMPORT_FIXED")
