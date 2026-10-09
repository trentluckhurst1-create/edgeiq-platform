# EDGEiQ — Out-of-Scope Path String Diagnostic (2026-10-10)

Authority: Grok AMEND — only previously extracted path strings from LAB245C3B_MARKET_SCHEMA_INVENTORY.csv and LAB245C3F_MARKET_ARCHIVE_CANDIDATE_RANK.csv. No referenced files opened; no existence checks or transformations applied.

## User-reported results
TOTAL_DISTINCT=6783
EXCLUDED_SP_BSP=72
RELATIVE=15
ABSOLUTE=0
WINDOWS_DRIVE=6696
UNC=0
IN_SCOPE_LEXICAL=0
OUT_OF_SCOPE=6711
OUT_OF_SCOPE_REPOSITORY_RELATIVE=15
OUT_OF_SCOPE_PREFIX_ONLY=471
POTENTIALLY_RECOVERABLE=471
OUT_OF_SCOPE_BY_TYPE: Relative=15, WindowsDrive=6696
TOP_APPARENT_ROOTS: C:=6696, data=14, public=1
STRING_ONLY_DIAGNOSTIC_COMPLETE

Reconciliation: 72 excluded + 6711 out of scope = 6783 distinct; 6696 Windows drive + 15 relative = 6711 out of scope. 471/6711 out-of-scope path strings contain an internal outputs or docs component with a following filename; the script calls them potentially recoverable solely on string form. 6240 others do not satisfy that specific test.

## Interpretation and limitations
Dominant issue is path-format/root mismatch: 6696 Windows drive paths are not lexically in scope under the active root. However, their actual directories, file existence, historical prices and pre-off timestamps are unverified. The root grouping collapses all Windows drive paths to 'C:' and cannot distinguish actual project roots. 'Repository-relative' is a classification of 15 relative strings, not proof of valid paths. The filename substring filter 'sp|bsp' may exclude unrelated names, but the 72 exclusions remain per authority.

## Disposition
STRING-ONLY DIAGNOSTIC COMPLETE / STOP. No additional archive search, path rewrite, referenced file opening, odds read, join or return calculation authorised. No certified price source; Stage011 historical profitability unknown.
