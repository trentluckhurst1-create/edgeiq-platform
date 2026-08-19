$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$componentPath = Join-Path $repoRoot "src\components\RaceIntelligenceScreen.tsx"
$stylePath = Join-Path $repoRoot "src\styles\edgeiqProductTerminalV1.css"
$indexStylePath = Join-Path $repoRoot "src\index.css"

$component = Get-Content -LiteralPath $componentPath -Raw
$styles = Get-Content -LiteralPath $stylePath -Raw
$indexStyles = Get-Content -LiteralPath $indexStylePath -Raw
$failures = New-Object System.Collections.Generic.List[string]

$meetingsStart = $component.IndexOf('if (productView === "MEETINGS")')
if ($meetingsStart -lt 0) {
  $failures.Add("MEETINGS product view is missing.")
  $meetingsBranch = ""
} else {
  $meetingsEnd = $component.IndexOf('if (!raceRows.length || !header)', $meetingsStart)
  if ($meetingsEnd -lt 0) { $meetingsEnd = $component.Length }
  $meetingsBranch = $component.Substring($meetingsStart, $meetingsEnd - $meetingsStart)
}

$raceStartNeedle = 'className="edgeiq-product-app edgeiq-product-race edgeiq-product-surface edgeiq-product-v4-page"'
$raceStart = $component.IndexOf($raceStartNeedle)
if ($raceStart -lt 0) {
  $failures.Add("Race branch is not mounted through edgeiq-product-v4-page.")
  $raceBranch = ""
} else {
  $raceEnd = $component.IndexOf('{fullHistoryRunner ?', $raceStart)
  if ($raceEnd -lt 0) { $raceEnd = $component.Length }
  $raceBranch = $component.Substring($raceStart, $raceEnd - $raceStart)
}

$requiredShellClasses = @(
  "edgeiq-product-v4-shell",
  "edgeiq-product-v4-top",
  "edgeiq-product-v4-hero",
  "edgeiq-product-v4-panel",
  "edgeiq-product-v4-table",
  "edgeiq-product-v4-section-title"
)

foreach ($className in $requiredShellClasses) {
  if (-not $component.Contains($className) -and -not $styles.Contains($className)) {
    $failures.Add("Missing shared shell class: $className")
  }
}

$oldActiveClasses = @(
  "edgeiq-race-product-shell",
  "edgeiq-race-product-topbar",
  "edgeiq-product-topbar",
  "edgeiq-race-account-panel",
  "edgeiq-product-user-chip",
  "edgeiq-race-primary-nav",
  "edgeiq-product-nav",
  "edgeiq-map-workspace",
  "edgeiq-product-workspace-premium",
  "edgeiq-race-premium-workspace"
)

foreach ($className in $oldActiveClasses) {
  if ($raceBranch.Contains($className)) {
    $failures.Add("Old workspace/header class remains active in race tabs: $className")
  }
  if ($meetingsBranch.Contains($className)) {
    $failures.Add("Old workspace/header class remains active in MEETINGS: $className")
  }
}

if (-not $component.Contains('className="edgeiq-home-v4"')) {
  $failures.Add("HOME v4 shell is missing.")
}
if (-not $meetingsBranch.Contains("edgeiq-product-v4-page") -or -not $meetingsBranch.Contains("edgeiq-product-v4-shell") -or -not $meetingsBranch.Contains("edgeiq-product-v4-top") -or -not $meetingsBranch.Contains("edgeiq-product-v4-hero")) {
  $failures.Add("MEETINGS is not mounted through the v4 page/shell/top/hero stack.")
}
if (-not $meetingsBranch.Contains("edgeiq-home-v4-brand") -or -not $raceBranch.Contains("edgeiq-home-v4-brand")) {
  $failures.Add("Internal tabs do not reuse the HOME EDGEiQ brand/logo classes.")
}
if (-not $meetingsBranch.Contains("edgeiq-home-v4-horse") -or -not $raceBranch.Contains("edgeiq-home-v4-horse")) {
  $failures.Add("Internal tab heroes do not reuse the HOME horse treatment.")
}
if (-not $meetingsBranch.Contains("edgeiq-home-v4-footer") -or -not $raceBranch.Contains("edgeiq-home-v4-footer")) {
  $failures.Add("Internal routes do not include the HOME footer language.")
}

$expectedTabs = @("RACE", "FIELD", "PERFORMANCE", "FORM", "MAP", "NEXUS", "MARKET", "RESULTS", "TRACK", "WEATHER")
foreach ($tab in $expectedTabs) {
  if (-not $component.Contains("label: `"$tab`"")) {
    $failures.Add("Expected tab label missing from live component: $tab")
  }
}

$panelCount = ([regex]::Matches($raceBranch, "edgeiq-product-v4-panel")).Count
$tableCount = ([regex]::Matches($raceBranch, "edgeiq-product-v4-table")).Count
if ($panelCount -lt 10) {
  $failures.Add("Expected at least 10 v4 tab panels including TRACK/WEATHER; found $panelCount.")
}
if ($tableCount -lt 5) {
  $failures.Add("Expected at least 5 v4 tables; found $tableCount.")
}

if (-not $styles.Contains("EDGEiQ REAL HOME SHELL V4")) {
  $failures.Add("Missing scoped HOME shell CSS marker.")
}
if (-not $styles.Contains(".edgeiq-product-v4-shell [style*=`"rgba(80,120,180`"]")) {
  $failures.Add("Legacy blue inline panel neutraliser is missing.")
}
if (-not $styles.Contains("linear-gradient(180deg, #071018 0%, #020508 100%)")) {
  $failures.Add("HOME background gradient is not present in v4 shell CSS.")
}
if (-not $styles.Contains("EDGEiQ SHELL FIX V6")) {
  $failures.Add("Missing V6 typography/meetings CSS marker.")
}
if (-not $styles.Contains("EDGEiQ FINAL VISUAL CLONE PASS")) {
  $failures.Add("Missing final HOME visual clone CSS marker.")
}
if (-not $styles.Contains("EDGEiQ HOME SCREENSHOT MATCH")) {
  $failures.Add("Missing screenshot-match CSS layer for HOME brand/horse/background reuse.")
}
if (-not $styles.Contains("EDGEiQ HOME MOCKUP LOCK")) {
  $failures.Add("Missing HOME mock-up lock CSS layer for RACE/FIELD.")
}
if (-not $styles.Contains("EDGEiQ PERFORMANCE TAB REBUILD V2")) {
  $failures.Add("Missing PERFORMANCE tab rebuild V2 CSS layer.")
}
if (-not $styles.Contains("font-size: clamp(30px, 2.4vw, 34px)")) {
  $failures.Add("V4 hero title is not capped at the restrained V6 scale.")
}
if ($styles.Contains("font-size: clamp(38px, 4.2vw, 72px) !important;") -and -not $styles.Contains("EDGEiQ SHELL FIX V6")) {
  $failures.Add("Oversized v4 hero title remains without V6 override.")
}
if (-not $indexStyles.Contains("radial-gradient(circle at 72% 18%, rgba(67,239,198,.08), transparent 28%)") -or -not $indexStyles.Contains("background-color: #020508 !important")) {
  $failures.Add("html/body/#root are not pinned to the HOME black background.")
}
if (-not $styles.Contains("body,`r`n#root") -and -not $styles.Contains("body,`n#root")) {
  $failures.Add("Final CSS does not explicitly neutralise body/#root side gutters.")
}
if (-not $raceBranch.Contains('edgeiq-product-v4-fact-grid')) {
  $failures.Add("TRACK/WEATHER v4 fact-grid views are missing from the race branch.")
}
foreach ($className in @("edgeiq-race-mock-tab", "edgeiq-race-mock-card-grid", "edgeiq-race-mock-runner-board", "edgeiq-field-lock-v1")) {
  if (-not $raceBranch.Contains($className)) {
    $failures.Add("Mock-up lock class missing from race branch: $className")
  }
}
if (-not $raceBranch.Contains('setIntelMode("FORM")')) {
  $failures.Add("Runner selection does not navigate into FORM.")
}
if ($raceBranch.Contains("edgeiq-field-guide-expansion")) {
  $failures.Add("FIELD tab still contains expandable in-place form guide content.")
}
foreach ($column in @("BARRIER", "WEIGHT", "EDGE %", "STATUS")) {
  if (-not $raceBranch.Contains($column)) {
    $failures.Add("RACE runner board column missing: $column")
  }
}
if (-not $raceBranch.Contains("edgeiq-performance-rebuild-v2") -or -not $raceBranch.Contains("edgeiq-performance-index-table")) {
  $failures.Add("PERFORMANCE tab is not using the V2 workstation table.")
}
foreach ($column in @("NO", "SILK", "HORSE", "EPI", "CURRENT", "PEAK", "AVG", "LAST", "L5", "L4", "L3", "L2", "L1")) {
  if (-not $raceBranch.Contains($column)) {
    $failures.Add("PERFORMANCE V2 column missing: $column")
  }
}
if ($raceBranch.Contains("['NO','HORSE','EPI','CURRENT','PEAK','AVG','LAST','TREND','GAP','L5','L4','L3','L2','L1','DIST','GOING','CLASS','PACE']")) {
  $failures.Add("Old PERFORMANCE columns remain active.")
}
if (-not $raceBranch.Contains("buildPerformanceRunCard") -or -not $raceBranch.Contains("setIntelMode(`"RESULTS`")")) {
  $failures.Add("PERFORMANCE historical cells are not wired to tooltip/results behaviour.")
}

if ($failures.Count -gt 0) {
  Write-Host "EDGEIQ_TAB_SHELL_V4_AUDIT: FAIL"
  foreach ($failure in $failures) {
    Write-Host "- $failure"
  }
  exit 1
}

Write-Host "EDGEIQ_TAB_SHELL_V4_AUDIT: PASS"
Write-Host "v4 shell classes present: $($requiredShellClasses -join ', ')"
Write-Host "v4 panels in race branch: $panelCount"
Write-Host "v4 tables in race branch: $tableCount"
Write-Host "old active workspace/header classes in race branch: 0"
Write-Host "MEETINGS v4 shell: present"
Write-Host "TRACK/WEATHER v4 tabs: present"
Write-Host "HOME brand/horse/footer reused: present"
Write-Host "RACE/FIELD mock-up lock: present"
Write-Host "PERFORMANCE V2 workstation: present"
Write-Host "root background: HOME black"
Write-Host "v4 hero title cap: 34px"
