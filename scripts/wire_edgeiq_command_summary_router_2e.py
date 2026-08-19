from pathlib import Path

root = Path.cwd()
router = root / "src/components/workspaces/EdgeiqWorkspaceRouter.tsx"

text = router.read_text(encoding="utf-8")

if "buildCommandExecutiveSummary" not in text:
    text = text.replace(
        'import { RaceCommandExecutiveWorkspace } from "./RaceCommandExecutiveWorkspace";',
        'import { RaceCommandExecutiveWorkspace } from "./RaceCommandExecutiveWorkspace";\nimport { buildCommandExecutiveSummary } from "../../services/buildCommandExecutiveSummary";'
    )

text = text.replace(
'''export function EdgeiqWorkspaceRouter({ commandWorkspace }: EdgeiqWorkspaceRouterProps) {
  const { activeSection, activeWorkspace } = useEdgeiqOs();''',
'''export function EdgeiqWorkspaceRouter({ commandWorkspace }: EdgeiqWorkspaceRouterProps) {
  const { activeSection, activeWorkspace } = useEdgeiqOs();
  const commandSummary = buildCommandExecutiveSummary();'''
)

text = text.replace(
'''        <RaceCommandExecutiveWorkspace legacyCommand={commandWorkspace} />''',
'''        <RaceCommandExecutiveWorkspace legacyCommand={commandWorkspace} summary={commandSummary} />'''
)

router.write_text(text, encoding="utf-8")
print("[EDGEIQ_COMMAND_2E] router now assembles COMMAND summary")
