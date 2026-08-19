from pathlib import Path

path = Path("src/components/shell/EdgeiqOsShell.tsx")
text = path.read_text(encoding="utf-8")

if 'EdgeiqWorkspace' not in text:
    text = text.replace(
        'import { useEdgeiqOs } from "../../state/edgeiqOsStore";',
        'import { EdgeiqWorkspace, useEdgeiqOs } from "../../state/edgeiqOsStore";'
    )

text = text.replace(
    '{["COMMAND", "FIELD", "MAP", "MARKET", "PERFORMANCE", "CONDITIONS"].map((workspace) => (',
    '{(["COMMAND", "FIELD", "MAP", "MARKET", "PERFORMANCE", "CONDITIONS"] as EdgeiqWorkspace[]).map((workspace) => ('
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ_OS_STORE_ROUTER_FIX] typed workspace nav array")
