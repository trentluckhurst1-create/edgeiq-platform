# FINAL LIVE RUNTIME WIRING MATRIX

Built: 2026-07-19
Repository: C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM
Branch: feature/component-refactor

Trace root:
- src/main.tsx mounts App/ProtectedApp and imports src/edgeiq-os/approved-ui/edgeiqApprovedUiRebuildV1.css.
- src/edgeiq-os/shell/EdgeiqOsShell.tsx mounts <RaceFileV3 />.
- src/edgeiq-os/race/RaceFileV3.tsx owns activeSection, viewLevel, selectedMeeting, selectedRace and maps primary navigation to viewLevel/race tabs.
- src/edgeiq-os/race/components/AppNavigation.tsx exposes primary navigation.
- src/edgeiq-os/race/components/RaceWorkspace.tsx owns race-level tab rendering.
- src/edgeiq-os/race/components/MeetingWorkspace.tsx owns meeting-level tab rendering.

| Workspace | Navigation destination | URL/view state | RaceFileV3 workspace key | Component currently mounted | Component expected to mount | Approved component available? | Legacy component involved? | Fallback component involved? | Current rendered result | Required runtime correction |
|---|---|---|---|---|---|---|---|---|---|---|
| HOME | Primary nav HOME | activeSection=home viewLevel=meetings | home | EdgeiqOsHome | EdgeiqOsHome | YES | NO | NO | Product HOME route | Verify approved HOME structure and encoding in live capture |
| MEETINGS | Primary nav MEETINGS | activeSection=meetings viewLevel=meetings | meetings | MeetingsWorkspace | MeetingsWorkspace | YES | NO | NO | Three-day meeting list | Verify compact columns and Open Meeting behaviour |
| RACE | Primary nav RACE after selected race | activeSection=race viewLevel=race initialTab=RACE | race | RaceWorkspace -> RaceIntelligenceWorkspace | RaceIntelligenceWorkspace | YES | NO | possible data-region fallback | Approved race route can mount | Ensure no whole-page collapse and record component |
| FIELD | Primary nav FIELD after selected race | activeSection=field viewLevel=race initialTab=FIELD | field | RaceWorkspace -> FieldWorkspace | FieldWorkspace | YES | NO | NO | Field route can mount | Record component and validate statuses/columns |
| FORM GUIDE | Primary nav FORM GUIDE after selected race | activeSection=formGuide viewLevel=race initialTab=FORM GUIDE | formGuide | RaceWorkspace -> RaceFormGuideWorkspace | RaceFormGuideWorkspace | YES | NO | possible historical-region fallback | Form route can mount | Keep structure when history unavailable |
| PERFORMANCE | Primary nav PERFORMANCE after selected race | activeSection=performance viewLevel=race initialTab=PERFORMANCE | performance | RaceWorkspace -> PerformanceWorkspace | PerformanceWorkspace | YES | NO | possible one-line data fallback | Performance route can mount | Retain matrix/regions under unavailable data |
| MAP | Primary nav MAP after selected race | activeSection=map viewLevel=race initialTab=MAP | map | RaceWorkspace -> MapWorkspace | MapWorkspace | YES | NO | speed unavailable lanes | Map route can mount | Verify active runners, right-to-left/barrier rules, component marker |
| EPI | Primary nav EPI after selected race | activeSection=epi viewLevel=race initialTab=EPI | epi | RaceWorkspace -> EpiWorkspaceWorkspace | EpiWorkspaceWorkspace | YES | NO | possible one-line data fallback | EPI route can mount | Retain current EPI structure under missing history |
| MARKET | Primary nav MARKET after selected race | activeSection=market viewLevel=race initialTab=MARKET | market | RaceWorkspace -> MarketWorkspace | MarketWorkspace | YES | NO | possible pending cells | Market route can mount | Ensure governed EDGEiQ/Fair values not blanked by market pending |
| OVERVIEW | Primary nav OVERVIEW after selected race | activeSection=overview viewLevel=race initialTab=OVERVIEW | overview | RaceWorkspace -> OverviewWorkspace | OverviewWorkspace | YES | NO | possible one-line data fallback | Overview route can mount | Retain overview sections under feed gaps |
| SCRATCHINGS | Meeting detail tab SCRATCHINGS | activeSection=meetings viewLevel=meeting tab=SCRATCHINGS | meeting:SCRATCHINGS | MeetingWorkspace -> MeetingScratchingsWorkspace | MeetingScratchingsWorkspace | YES | NO | possible pending detail regions | Reachable only after Open Meeting | Capture through live meeting tab and record component |
| GEAR CHANGES | Meeting detail tab GEAR CHANGES | activeSection=meetings viewLevel=meeting tab=GEAR_CHANGES | meeting:GEAR_CHANGES | MeetingWorkspace -> MeetingGearChangesWorkspace | MeetingGearChangesWorkspace | YES | NO | possible empty sections | Reachable only after Open Meeting | Capture through live meeting tab and record component |
| TRACK | Meeting detail tab TRACK | activeSection=meetings viewLevel=meeting tab=TRACK | meeting:TRACK | MeetingWorkspace -> MeetingTrackWorkspace | MeetingTrackWorkspace | YES | NO | possible unavailable panels | Reachable only after Open Meeting | Capture through live meeting tab and record component |
| WEATHER | Meeting detail tab WEATHER | activeSection=meetings viewLevel=meeting tab=WEATHER | meeting:WEATHER | MeetingWorkspace -> MeetingWeatherWorkspace | MeetingWeatherWorkspace | YES | NO | possible unavailable weather values | Reachable only after Open Meeting | Capture through live meeting tab and record component |
| RESULTS | Primary nav RESULTS currently global, meeting tab RESULTS also exists | activeSection=results OR meeting tab=RESULTS | results / meeting:RESULTS | GlobalResultsWorkspace -> MeetingResultsWorkspace, or MeetingWorkspace -> MeetingResultsWorkspace | MeetingResultsWorkspace/ResultsWorkspace per context | YES | Global wrapper ambiguity | YES when no meeting selected | Current primary nav can show select-meeting card | Route selected-race RESULTS to race-level Review/Results structure or record meeting-level intent honestly |
| INSIGHTS | Primary nav INSIGHTS after selected race | activeSection=insights viewLevel=race initialTab=INSIGHTS | insights | RaceWorkspace -> InsightsWorkspace | InsightsWorkspace | YES | NO | possible one-line data fallback | Insights route can mount | Retain categories/filters under unavailable data |
| LAB | Primary nav LAB | activeSection=lab viewLevel unchanged | lab | LabWorkspace | LabWorkspace | YES | possible alternate lab layout | NO | Dedicated lab route | Verify approved query-builder structure and component marker |
| COMPARE | Primary nav COMPARE | activeSection=compare viewLevel=runner mode=compare | compare | RunnerProfileWorkspace compare mode | CompareWorkspace | YES | YES | NO | Not mounting approved CompareWorkspace | Fix resolver to mount CompareWorkspace |
| REVIEW | Primary nav REVIEW after selected race | activeSection=review viewLevel=race initialTab=REVIEW | review | RaceWorkspace -> ReviewWorkspace | ReviewWorkspace | YES | NO | pending regions possible | Review route can mount | Retain full structure under pending results |
| SETTINGS | Primary nav SETTINGS | activeSection=settings | settings | SettingsWorkspace | SettingsWorkspace | YES | NO | NO | Settings route | Not one of approved 19, but shell conformance must remain |

Duplicate/ambiguous implementations found:
- RESULTS has GlobalResultsWorkspace, MeetingResultsWorkspace, ResultsWorkspace, ReviewWorkspace routes. Primary nav currently bypasses RaceWorkspace.
- COMPARE has src/edgeiq-os/compare/CompareWorkspace.tsx but primary nav routes to RunnerProfileWorkspace compare mode.
- Meeting-level SCRATCHINGS/GEAR/TRACK/WEATHER are live only as nested MeetingWorkspace tabs, not primary AppNavigation keys.
- Race-level sections are mediated by raceTabBySection in RaceFileV3 and then a separate tab switch in RaceWorkspace.

Placeholder/fallback strings requiring runtime validation:
- Select a meeting to review results.
- Restoring selected meeting.
- Governed historical/performance/overview/insight/EPI unavailable variants must not replace whole analytical workspaces.

Root runtime corrections before final audit:
- Add explicit canonical component-resolution metadata for all 19 approved workspaces.
- Mount CompareWorkspace for primary COMPARE.
- Resolve primary RESULTS with selected race through race-level RESULTS/REVIEW structure instead of global select-meeting fallback.
- Add data attributes/component names so live browser capture proves actual mounted components.
- Ensure capture reaches meeting-level SCRATCHINGS/GEAR/TRACK/WEATHER through Open Meeting tabs, and race-level tabs through primary nav after Open Race.
