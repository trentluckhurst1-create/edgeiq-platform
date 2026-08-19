from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8-sig")

config_dir = root / "src" / "config"
config_dir.mkdir(exist_ok=True)

files_config = config_dir / "edgeiqFiles.ts"
files_config.write_text('''export const FILES = {
  runnerBoard: "/data/edgeiq_live_runner_board_governed_v1.csv",
  runnerIntel: "/data/edgeiq_runner_intelligence_v1.csv",
  v8: "/data/edgeiq_live_v8_candidate_display_feed_v1.csv",
  betQuality: "/data/edgeiq_live_bet_quality_v1_1.csv",
  reliability: "/data/edgeiq_live_race_reliability_v1_feed.csv",
  intelligenceCards: "/data/edgeiq_race_intelligence_cards_v1.csv",
  briefing: "/data/edgeiq_race_briefing_v1.csv",
  marketIntel: "/data/edgeiq_market_intelligence_v1.csv",
  verdict: "/data/edgeiq_race_verdict_v1.csv",
  trackIntel: "/data/edgeiq_track_intelligence_card_v1.csv",
  horseDrawer: "/data/edgeiq_horse_intelligence_drawer_current.csv",
  runnerDnaDrawer: "/data/edgeiq_runner_dna_drawer_feed_v2.csv",
  explainability: "/data/edgeiq_explainability_terminal_feed_v1_2.csv",
  connectionIntelligence: "/data/edgeiq_connection_intelligence_v2_1.csv",
  factorScorecard: "/data/edgeiq_factor_lab_enrichment_feed_v1.csv",
  limited: "/data/edgeiq_limited_data_market_adjusted_v1.csv",
  intelligenceScore: "/data/edgeiq_live_intelligence_score_v1.csv",
  customerIntelligence: "/data/edgeiq_customer_intelligence_terminal_feed_v1_1.csv",
  intelligenceSummary: "/data/edgeiq_intelligence_summary_engine_v1_2.csv",
  raceDayIntelligence: "/data/edgeiq_race_day_intelligence_card_v1_1.csv",
  runnerProfile: "/data/edgeiq_runners_enrichment_feed_v1_1.csv",
  formIntelligence: "/data/edgeiq_form_intelligence_v2.csv",
  runnerForm: "/data/edgeiq_runner_form_engine_current.csv",
  formEnrichment: "/data/edgeiq_form_enrichment_feed_v4.csv",
  runnerFormHistory: "/data/runner_form_history.csv",
  historyMaster: "/data/edgeiq_empty_terminal_feed_v1.csv",
  historyDetail: "/data/edgeiq_runner_history_detail_v1.csv",
  horseCareer: "/data/edgeiq_empty_terminal_feed_v1.csv",
  horserchetype: "/data/edgeiq_empty_terminal_feed_v1.csv",
  horseTrajectory: "/data/edgeiq_empty_terminal_feed_v1.csv",
  horseProjection: "/data/edgeiq_empty_terminal_feed_v1.csv",
  campaignIntelligence: "/data/edgeiq_campaign_intelligence_engine_v1_1.csv",
  hiddenGem: "/data/edgeiq_current_hidden_gem_feed_v1_1.csv",
  raceShapeFallback: "/data/edgeiq_race_shape_fallback_engine_v1.csv",
  mapEnrichment: "/data/edgeiq_map_enrichment_feed_v3.csv",
  chaosIndex: "/data/edgeiq_chaos_index_v1.csv",
  opportunityScore: "/data/edgeiq_opportunity_score_v1.csv",
  commandEnrichment: "/data/edgeiq_command_enrichment_feed_v3.csv",
  ratingsHeatmap: "/data/edgeiq_ratings_intelligence_heatmap_v1.csv",
  productMeetings: "/data/edgeiq_product_shell_meetings_v1.csv",
  raceList: "/data/edgeiq_vic_three_day_race_list_v1.csv",
  meetingCalendar: "/data/edgeiq_vic_three_day_meeting_calendar_v1.csv",
  liveTrackIntelligence: "/data/edgeiq_live_track_intelligence_v2_1.csv",
  trackMapManifest: "/data/edgeiq_track_map_manifest_v1.csv",
  nexusContextual: "/data/edgeiq_live_nexus_contextual_feed_v2_1.csv",
  nexusContextualFallback: "/data/edgeiq_live_nexus_contextual_feed_v2.csv",
  formSectionalProfile: "/data/edgeiq_form_sectional_terminal_feed_v1.csv",
  gearProfile: "/data/edgeiq_gear_terminal_feed_v1.csv",
  labPriceEngine: "/data/edgeiq_lab_price_engine_feed_v1.csv",
} as const;
''', encoding="utf-8")

text, count = re.subn(r'\nconst FILES = \{.*?\n\};\n', '\n', text, count=1, flags=re.S)
if count != 1:
    raise SystemExit("[ERROR] FILES block not replaced")

import_line = 'import { FILES } from "../config/edgeiqFiles";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")

print("[FILES_CONFIG_EXTRACT] complete")
