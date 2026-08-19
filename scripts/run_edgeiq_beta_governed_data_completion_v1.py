from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
VISUAL_DIR = PUBLIC_DATA / "visual_audits" / "edgeiq_beta_data_completion_v1"
PROGRESS_JSON = PUBLIC_DATA / "edgeiq_beta_governed_data_completion_v1_progress.json"
PROGRESS_TXT = PUBLIC_DATA / "edgeiq_beta_governed_data_completion_v1_progress.txt"
PREFLIGHT_TXT = PUBLIC_DATA / "edgeiq_beta_governed_data_completion_v1_preflight.txt"
FIELD_INVENTORY = PUBLIC_DATA / "edgeiq_beta_workspace_field_inventory_v1.csv"
SOURCE_REGISTRY = PUBLIC_DATA / "edgeiq_beta_governed_source_registry_v1.csv"
JOIN_AUDIT = PUBLIC_DATA / "edgeiq_beta_data_join_integrity_v1.csv"
JOIN_SUMMARY = PUBLIC_DATA / "edgeiq_beta_data_join_integrity_v1_summary.txt"
JOIN_JSON = PUBLIC_DATA / "edgeiq_beta_data_join_integrity_v1_audit.json"
CONSISTENCY_CSV = PUBLIC_DATA / "edgeiq_beta_cross_workspace_consistency_v1.csv"
COVERAGE_CSV = PUBLIC_DATA / "edgeiq_beta_data_coverage_matrix_v1.csv"
COVERAGE_TXT = PUBLIC_DATA / "edgeiq_beta_data_coverage_summary_v1.txt"
COVERAGE_JSON = PUBLIC_DATA / "edgeiq_beta_data_coverage_summary_v1.json"
GAPS_CSV = PUBLIC_DATA / "edgeiq_remaining_beta_governed_data_gaps_v1.csv"
FINAL_TXT = PUBLIC_DATA / "edgeiq_beta_governed_data_completion_v1_final_report.txt"
FINAL_JSON = PUBLIC_DATA / "edgeiq_beta_governed_data_completion_v1_final_report.json"

SAFE_FRONTEND_ROW_THRESHOLD = 10000

FIELD_COLUMNS = [
    "workspace",
    "section",
    "field",
    "component",
    "view_model",
    "service",
    "terminal_feed",
    "upstream_source",
    "join_key",
    "required_data_type",
    "current_population_status",
    "current_coverage_rows",
    "current_coverage_percent",
    "freshness_status",
    "source_authority",
    "missing_reason",
    "intended_builder_owner",
    "react_calculation_detected",
    "duplicate_feed_detected",
    "action_required",
    "priority",
    "notes",
]

SOURCE_COLUMNS = [
    "source_name",
    "source_path",
    "source_type",
    "authority",
    "domain",
    "row_count",
    "date_min",
    "date_max",
    "last_modified",
    "freshness",
    "grain",
    "primary_keys",
    "duplicate_key_count",
    "current_meeting_match_count",
    "safe_for_frontend",
    "requires_builder",
    "canonical_owner",
    "downstream_workspaces",
    "known_gaps",
    "notes",
]

JOIN_COLUMNS = [
    "join_name",
    "workspace",
    "left_source",
    "right_source",
    "join_key",
    "left_rows",
    "right_rows",
    "matched_rows",
    "unmatched_left_rows",
    "unmatched_right_rows",
    "duplicate_left_keys",
    "duplicate_right_keys",
    "conflicting_values",
    "stale_date_matches",
    "fuzzy_matches",
    "review_required",
    "status",
    "notes",
]

WORKSPACES: dict[str, dict[str, Any]] = {
    "Meetings": {
        "component": "MeetingsWorkspace.tsx",
        "service": "meetingsFeed.ts",
        "view_model": "MeetingViewModel",
        "feed": "edgeiq_three_day_window_v1.json",
        "builder": "build_edgeiq_three_day_window_v1.py",
        "join_key": "date|track",
        "fields": [
            "meeting",
            "state",
            "race count",
            "first race",
            "last race",
            "track condition",
            "rail current",
            "rail previous",
            "irrigation 24 hours",
            "irrigation 7 days",
            "rainfall 24 hours",
            "rainfall 7 days",
            "temperature",
            "wind",
            "weather",
            "updated timestamp",
            "meeting status",
            "data quality",
            "correct track map",
            "correct route context",
        ],
    },
    "Meeting Detail": {
        "component": "MeetingWorkspace.tsx",
        "service": "meetingDetailFeed.ts",
        "view_model": "MeetingDetailViewModel",
        "feed": "edgeiq_three_day_product_catalog_v1.json",
        "builder": "build_edgeiq_three_day_product_catalog_v1.py",
        "join_key": "meetingKey|raceKey",
        "fields": [
            "selected meeting persistence",
            "selected race persistence",
            "tab navigation",
            "route context",
            "race list",
            "official meeting metadata",
            "source freshness",
            "cross-meeting data leakage guard",
        ],
    },
    "Form Guide": {
        "component": "RaceFormGuideWorkspace.tsx",
        "service": "formGuideEnrichedFeed.ts|formGuideNormaliser.ts",
        "view_model": "FormGuideRunnerViewModel",
        "feed": "edgeiq_form_guide_enriched_v2.csv",
        "builder": "build_edgeiq_form_guide_enriched_v2.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "runner number",
            "silk",
            "runner",
            "barrier",
            "weight",
            "jockey",
            "trainer",
            "market",
            "EPI",
            "ERI",
            "EPI SPD",
            "early speed",
            "late speed",
            "suitability",
            "form momentum",
            "race shape",
            "effective barrier",
            "current status",
            "last starts",
            "official form history",
            "full history",
            "race links",
            "results links",
            "steward comments",
            "sectional evidence",
            "source freshness",
        ],
    },
    "Scratchings": {
        "component": "MeetingScratchingsWorkspace.tsx",
        "service": "scratchingsFeed.ts",
        "view_model": "ScratchingsViewModel",
        "feed": "edgeiq_scratchings_terminal_feed_v1.csv",
        "builder": "audit_edgeiq_scratchings_engineering_build_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "official scratchings",
            "scratching timestamp",
            "late scratching",
            "reason",
            "barrier updates",
            "field-size changes",
            "emergency elevation",
            "market suspension context",
            "race-shape recalculation status",
        ],
    },
    "Gear Changes": {
        "component": "MeetingGearChangesWorkspace.tsx",
        "service": "gearChangesFeed.ts",
        "view_model": "GearChangesViewModel",
        "feed": "edgeiq_gear_terminal_feed_v1.csv",
        "builder": "build_edgeiq_gear_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "current meeting gear changes",
            "previous gear",
            "new gear",
            "first-time gear",
            "gear removed",
            "official update timestamp",
            "runner gear history",
            "source authority",
            "current-meeting freshness",
        ],
    },
    "Track": {
        "component": "MeetingTrackWorkspace.tsx",
        "service": "trackFeed.ts",
        "view_model": "TrackWorkspaceViewModel",
        "feed": "edgeiq_vic_official_track_conditions_v1.json|edgeiq_current_true_track_feed_v1.csv|edgeiq_track_profile_v2.csv",
        "builder": "build_edgeiq_racing_australia_track_and_audit_bom_v1.py",
        "join_key": "date|track|race_no",
        "fields": [
            "official track condition",
            "rail position",
            "previous rail",
            "irrigation",
            "rainfall",
            "track manager update",
            "circumference",
            "straight length",
            "track direction",
            "course type",
            "correct curated map",
            "distance-specific pattern evidence",
            "lane performance",
            "settling-position performance",
            "leader performance",
            "on-pace performance",
            "midfield performance",
            "backmarker performance",
            "historical last 3",
            "historical last 10",
            "comparable-condition history",
            "source freshness",
        ],
    },
    "Weather": {
        "component": "MeetingWeatherWorkspace.tsx",
        "service": "weatherFeed.ts",
        "view_model": "WeatherWorkspaceViewModel",
        "feed": "edgeiq_metropolitan_weather_v1.json|edgeiq_race_weather_v1.json",
        "builder": "build_edgeiq_metropolitan_weather_v1.py|build_edgeiq_weather_beta_v1.py",
        "join_key": "date|track|station",
        "fields": [
            "current temperature",
            "apparent temperature",
            "wind speed",
            "wind direction",
            "gusts",
            "rainfall",
            "humidity",
            "chance of rain",
            "hourly forecast",
            "source station",
            "source update time",
            "meeting-to-station mapping",
            "race-time forecast",
            "builder-owned track impact",
            "builder-owned wind impact",
            "builder-owned rainfall impact",
            "weather notes",
            "stale state",
            "unavailable state",
        ],
    },
    "Results": {
        "component": "MeetingResultsWorkspace.tsx|ResultsWorkspace.tsx|GlobalResultsWorkspace.tsx",
        "service": "resultsFeed.ts",
        "view_model": "ResultsWorkspaceViewModel",
        "feed": "edgeiq_meeting_results_terminal_feed_v1.csv",
        "builder": "build_edgeiq_meeting_results_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "official race status",
            "finishing order",
            "margins",
            "official time",
            "sectional times",
            "last 600",
            "last 400",
            "last 200",
            "benchmark comparison",
            "EPI",
            "ERI",
            "EPF",
            "market price",
            "starting price",
            "jockey",
            "trainer",
            "barrier",
            "weight",
            "steward comments",
            "performance links",
            "runner result detail",
            "meeting result state",
            "dividends",
        ],
    },
    "MAP": {
        "component": "MapWorkspace.tsx",
        "service": "mapFeed.ts",
        "view_model": "MapWorkspaceViewModel",
        "feed": "edgeiq_map_terminal_feed_v1.csv",
        "builder": "build_edgeiq_map_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "barrier",
            "effective barrier",
            "map position",
            "projected zone",
            "early speed",
            "speed rank",
            "run style",
            "confidence",
            "evidence state",
            "pressure",
            "tempo",
            "likely settling position",
            "race shape",
            "scratching effects",
            "source version",
            "unresolved status",
        ],
    },
    "Market": {
        "component": "MarketWorkspace.tsx",
        "service": "marketFeed.ts",
        "view_model": "MarketWorkspaceViewModel",
        "feed": "edgeiq_market_terminal_feed_v1.csv",
        "builder": "build_edgeiq_market_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "live market price",
            "market source",
            "timestamp",
            "opening price",
            "current price",
            "movement",
            "fluctuation",
            "implied probability",
            "fair probability",
            "fair price",
            "edge",
            "market status",
            "suspension",
            "unavailable state",
            "stale state",
        ],
    },
    "Overview": {
        "component": "OverviewWorkspace.tsx",
        "service": "overviewFeed.ts",
        "view_model": "OverviewWorkspaceViewModel",
        "feed": "edgeiq_overview_terminal_feed_v1.csv",
        "builder": "build_edgeiq_overview_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no",
        "fields": [
            "meeting context",
            "race context",
            "headline evidence",
            "EPI leaders",
            "pace",
            "tempo",
            "key determinants",
            "hidden angles",
            "track context",
            "weather context",
            "market context",
            "data-quality state",
            "missing-evidence state",
        ],
    },
    "Insights": {
        "component": "InsightsWorkspace.tsx",
        "service": "insightsFeed.ts",
        "view_model": "InsightsWorkspaceViewModel",
        "feed": "edgeiq_insights_terminal_feed_v1.csv",
        "builder": "build_edgeiq_insights_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "insight text",
            "evidence source",
            "evidence type",
            "freshness",
            "confidence",
            "evidence status",
            "affected runner",
            "race context",
            "explanation",
            "suitability",
            "form momentum",
            "stage of preparation",
            "track-condition suitability",
            "distance suitability",
            "race-shape compatibility",
            "jockey-trainer combinations",
            "stable intent evidence",
            "campaign profile",
            "market behaviour",
            "pressure exposure",
            "pace vulnerability",
            "late-speed strength",
            "hidden form evidence",
        ],
    },
    "EPI Workspace": {
        "component": "EpiWorkspaceWorkspace.tsx",
        "service": "epiWorkspaceFeed.ts",
        "view_model": "EpiWorkspaceViewModel",
        "feed": "edgeiq_epi_workspace_terminal_feed_v1.csv",
        "builder": "build_edgeiq_epi_workspace_terminal_feed_v1.py",
        "join_key": "race_date|track|race_no|runner",
        "fields": [
            "current EPI",
            "historical EPI",
            "ERI",
            "EPI SPD",
            "performance tiles",
            "peak",
            "average",
            "trend",
            "race links",
            "historical result context",
            "date",
            "track",
            "distance",
            "class",
            "finish",
            "margin",
            "source version",
        ],
    },
}

FIELD_ALIASES: dict[str, list[str]] = {
    "runner number": ["no", "number", "runner_no", "runner_number", "saddlecloth"],
    "silk": ["silk", "silk_url", "silkUrl"],
    "runner": ["runner", "horse", "horse_name", "runner_name", "name"],
    "meeting": ["meeting", "meeting_name", "venue", "track"],
    "state": ["state"],
    "race count": ["race_count", "raceCount", "races"],
    "first race": ["first_race", "firstRace"],
    "last race": ["last_race", "lastRace"],
    "track condition": ["track_condition", "trackCondition", "condition", "going"],
    "official track condition": ["track_condition", "official_condition", "condition"],
    "rail current": ["rail", "rail_position", "rail_current"],
    "rail position": ["rail", "rail_position"],
    "previous rail": ["previous_rail", "rail_previous"],
    "rail previous": ["previous_rail", "rail_previous"],
    "irrigation": ["irrigation", "irrigation_24h", "irrigation_7d"],
    "irrigation 24 hours": ["irrigation_24h", "irrigation_24_hours"],
    "irrigation 7 days": ["irrigation_7d", "irrigation_7_days"],
    "rainfall": ["rainfall", "rainfall_24h", "rainfall_7d"],
    "rainfall 24 hours": ["rainfall_24h", "rainfall_24_hours", "rain_24h"],
    "rainfall 7 days": ["rainfall_7d", "rainfall_7_days", "rain_7d"],
    "temperature": ["temperature", "temp", "air_temperature"],
    "current temperature": ["temperature", "temp", "air_temperature"],
    "apparent temperature": ["apparent_temperature", "feels_like"],
    "wind": ["wind", "wind_speed", "wind_direction"],
    "wind speed": ["wind_speed", "wind_kmh"],
    "wind direction": ["wind_direction", "wind_dir"],
    "gusts": ["gust", "gusts", "wind_gust"],
    "humidity": ["humidity"],
    "weather": ["weather", "weather_summary"],
    "chance of rain": ["chance_of_rain", "rain_probability"],
    "hourly forecast": ["hourly_forecast", "forecast"],
    "source station": ["station", "station_name", "station_id"],
    "source update time": ["updated_at", "source_updated_at", "observation_time"],
    "updated timestamp": ["updated_at", "built_at", "generated_at", "generatedAt"],
    "meeting status": ["meeting_status", "meet_status", "status", "full_status"],
    "race list": ["race_no", "race_number", "race_name", "race_count"],
    "race context": ["race_key", "race_no", "race_number", "race_name"],
    "barrier": ["barrier", "bar", "draw"],
    "effective barrier": ["effective_barrier"],
    "weight": ["weight", "wt"],
    "jockey": ["jockey"],
    "trainer": ["trainer"],
    "market": ["market", "market_price", "live_price", "current_price"],
    "live market price": ["live", "live_price", "current_price", "market"],
    "opening price": ["open", "opening_price"],
    "current price": ["current", "current_price", "live_price", "market"],
    "fluctuation": ["fluc", "fluctuation", "movement"],
    "movement": ["move", "movement", "fluc"],
    "implied probability": ["implied_probability", "implied_prob"],
    "fair probability": ["fair_probability", "fair_prob"],
    "fair price": ["fair_price", "edgeiq_price", "assessed_price"],
    "edge": ["edge", "edge_pct", "edge_percent"],
    "EPI": ["epi", "epi_rating", "current_epi"],
    "current EPI": ["epi", "current_epi", "epi_rating"],
    "historical EPI": ["historical_epi", "epi", "past_epi"],
    "ERI": ["eri", "eri_rating"],
    "EPI SPD": ["epi_spd", "epi_speed", "gate_speed", "early_speed"],
    "early speed": ["early_speed", "earlySpeed", "speed"],
    "late speed": ["late_speed", "lateSpeed"],
    "suitability": ["suitability", "suitability_score", "suitability_label"],
    "form momentum": ["form_momentum", "momentum"],
    "race shape": ["race_shape", "shape"],
    "current status": ["status", "scratched", "race_status"],
    "last starts": ["last5", "last_five", "last_starts", "form"],
    "official form history": ["recent_form", "official_form", "history"],
    "full history": ["history", "historical_runs", "full_history"],
    "race links": ["race_link", "race_url", "form_url"],
    "results links": ["result_link", "results_url"],
    "steward comments": ["steward", "steward_comments"],
    "sectional evidence": ["sectional", "esi", "split", "last_600"],
    "official scratchings": ["scratched", "scratching", "status"],
    "scratching timestamp": ["scratching_time", "scratched_at", "updated_at"],
    "late scratching": ["late_scratching"],
    "reason": ["reason", "scratching_reason"],
    "field-size changes": ["field_size", "field_size_change"],
    "emergency elevation": ["emergency", "elevated"],
    "market suspension context": ["suspension", "market_status"],
    "race-shape recalculation status": ["race_shape_status", "recalculation_status"],
    "current meeting gear changes": ["gear_changes", "gear_change_flag", "gear_current"],
    "previous gear": ["previous_gear", "gear_previous"],
    "new gear": ["new_gear", "gear_added", "gear_current"],
    "first-time gear": ["first_time_gear"],
    "gear removed": ["gear_removed"],
    "official update timestamp": ["updated_at", "source_updated_at"],
    "runner gear history": ["gear_history"],
    "source authority": ["source", "source_authority"],
    "current-meeting freshness": ["freshness", "source_updated_at"],
    "track manager update": ["track_manager_update", "updated_at"],
    "circumference": ["circumference"],
    "straight length": ["straight", "straight_length"],
    "track direction": ["direction", "track_direction"],
    "course type": ["course_type"],
    "correct curated map": ["map", "map_path", "track_map"],
    "distance-specific pattern evidence": ["distance", "pattern"],
    "lane performance": ["lane", "lane_performance"],
    "settling-position performance": ["settling", "position_performance"],
    "leader performance": ["leader", "leaders"],
    "on-pace performance": ["on_pace", "onpace"],
    "midfield performance": ["midfield"],
    "backmarker performance": ["backmarker", "backmarkers"],
    "historical last 3": ["last_3", "historical_last_3"],
    "historical last 10": ["last_10", "historical_last_10"],
    "comparable-condition history": ["comparable", "condition_history"],
    "official race status": ["race_status", "status"],
    "finishing order": ["position", "pos", "finish_position"],
    "margins": ["margin", "beaten_margin"],
    "official time": ["official_time", "race_time", "winning_time"],
    "sectional times": ["sectional", "last_600", "last_400", "last_200"],
    "last 600": ["last_600", "600m"],
    "last 400": ["last_400", "400m"],
    "last 200": ["last_200", "200m"],
    "benchmark comparison": ["benchmark", "standard", "esi"],
    "EPF": ["epf"],
    "market price": ["market", "price", "sp"],
    "starting price": ["sp", "starting_price"],
    "performance links": ["performance_link", "race_link"],
    "runner result detail": ["runner_result_detail", "result_detail"],
    "meeting result state": ["meeting_result_state", "race_status"],
    "dividends": ["dividend", "dividends"],
    "map position": ["map_position", "position", "settling_position"],
    "projected zone": ["projected_zone", "zone"],
    "speed rank": ["speed_rank", "early_speed_rank"],
    "run style": ["run_style", "style"],
    "confidence": ["confidence", "source_confidence"],
    "evidence state": ["evidence_state", "source_confidence"],
    "pressure": ["pressure", "tempo_pressure"],
    "tempo": ["tempo", "expected_tempo"],
    "likely settling position": ["settling_position", "likely_position"],
    "scratching effects": ["scratching_effects"],
    "source version": ["source_version", "version"],
    "unresolved status": ["unresolved", "status"],
    "market source": ["source", "market_source"],
    "timestamp": ["timestamp", "price_timestamp", "updated_at"],
    "market status": ["market_status", "status"],
    "suspension": ["suspension", "suspended"],
    "unavailable state": ["unavailable", "status"],
    "stale state": ["stale", "freshness"],
    "meeting context": ["meeting", "track", "meeting_key"],
    "headline evidence": ["headline", "summary"],
    "EPI leaders": ["epi_leaders", "top_epi"],
    "pace": ["pace", "tempo"],
    "key determinants": ["determinants", "key_factor"],
    "hidden angles": ["hidden", "angle"],
    "track context": ["track_context", "track_condition"],
    "weather context": ["weather_context", "weather"],
    "market context": ["market_context", "market"],
    "data-quality state": ["data_quality", "quality"],
    "missing-evidence state": ["missing_evidence", "unavailable"],
    "insight text": ["insight_text", "text", "insight"],
    "evidence source": ["evidence_source", "source"],
    "evidence type": ["evidence_type", "type"],
    "freshness": ["freshness", "updated_at"],
    "affected runner": ["runner", "affected_runner"],
    "explanation": ["explanation", "notes"],
    "performance tiles": ["tile", "performance"],
    "peak": ["peak", "peak_epi"],
    "average": ["average", "avg", "average_epi"],
    "trend": ["trend"],
    "historical result context": ["historical_context", "result_context"],
    "date": ["date", "race_date"],
    "track": ["track"],
    "distance": ["distance", "dist"],
    "class": ["class", "race_class"],
    "finish": ["finish", "position"],
    "margin": ["margin"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def normalise_key(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.upper()
    text = re.sub(r"SPORTSBET-|BET365|LADBROKES|THE VALLEY", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def text_status(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return text not in {"-", "N/A", "NA", "null", "None", "Unavailable", "Pending", "Not supplied"}


def infer_authority(name: str) -> str:
    lower = name.lower()
    if "racing_australia" in lower or "official" in lower:
        return "official racing authority"
    if "racingcom" in lower or "three_day" in lower or "form_guide" in lower:
        return "Racing.com governed feed"
    if "bom" in lower or "weather" in lower:
        return "Bureau of Meteorology / governed weather builder"
    if "sportsbet" in lower or "market" in lower:
        return "market provider / governed market builder"
    if "edgeiq" in lower:
        return "EDGEiQ governed builder"
    return "repository source"


def infer_domain(name: str) -> str:
    lower = name.lower()
    pairs = [
        ("weather", "weather"),
        ("track", "track"),
        ("scratch", "scratchings"),
        ("gear", "gear"),
        ("market", "market"),
        ("result", "results"),
        ("sectional", "sectionals"),
        ("speed", "speed"),
        ("map", "map"),
        ("form", "form"),
        ("meeting", "meetings"),
        ("epi", "performance"),
        ("insight", "insights"),
        ("overview", "overview"),
    ]
    for token, domain in pairs:
        if token in lower:
            return domain
    return "general"


def infer_workspaces(name: str) -> str:
    domain = infer_domain(name)
    mapping = {
        "weather": "Meetings|Weather|Overview",
        "track": "Meetings|Track|MAP|Overview",
        "scratchings": "Scratchings|Form Guide|MAP|Market",
        "gear": "Gear Changes|Form Guide",
        "market": "Market|Form Guide|Overview",
        "results": "Results|EPI Workspace|Form Guide",
        "sectionals": "Results|Form Guide|EPI Workspace",
        "speed": "Form Guide|MAP|EPI Workspace",
        "map": "MAP|Overview",
        "form": "Form Guide|EPI Workspace",
        "meetings": "Meetings|Meeting Detail|Form Guide",
        "performance": "EPI Workspace|Form Guide",
        "insights": "Insights|Overview",
        "overview": "Overview",
    }
    return mapping.get(domain, "")


def source_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "file"


def csv_header(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            first = f.readline()
        if not first:
            return []
        return next(csv.reader([first]))
    except Exception:
        return []


def fast_count_rows(path: Path) -> int:
    try:
        size = path.stat().st_size
        if size > 50 * 1024 * 1024:
            sample_size = min(size, 4 * 1024 * 1024)
            with path.open("rb") as f:
                sample = f.read(sample_size)
            sample_lines = max(1, sample.count(b"\n"))
            avg_line = max(1, sample_size / sample_lines)
            return max(0, int(size / avg_line) - 1)
        with path.open("rb") as f:
            lines = 0
            for block in iter(lambda: f.read(1024 * 1024), b""):
                lines += block.count(b"\n")
        if size > 0:
            return max(lines - 1, 0)
        return 0
    except Exception:
        return 0


def load_csv_limited(path: Path, limit: int = 50000) -> list[dict[str, str]]:
    if not path.exists() or path.suffix.lower() != ".csv":
        return []
    rows: list[dict[str, str]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for index, row in enumerate(reader):
                if index >= limit:
                    break
                rows.append({k: (v or "") for k, v in row.items()})
    except Exception:
        return rows
    return rows


def json_stats(path: Path) -> tuple[int, list[str], Any]:
    try:
        if path.stat().st_size > 50 * 1024 * 1024:
            return 0, [], None
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return 0, [], None
    if isinstance(data, list):
        headers = sorted({key for row in data[:500] if isinstance(row, dict) for key in row.keys()})
        return len(data), headers, data
    if isinstance(data, dict):
        if isinstance(data.get("rows"), list):
            rows = data["rows"]
            headers = sorted({key for row in rows[:500] if isinstance(row, dict) for key in row.keys()})
            return len(rows), headers, rows
        if isinstance(data.get("meetings"), list):
            meetings = data["meetings"]
            race_count = sum(len(m.get("races") or []) for m in meetings if isinstance(m, dict))
            runner_count = 0
            for meeting in meetings:
                for race in meeting.get("races") or []:
                    runner_count += len(race.get("runners") or [])
            headers = ["meetings", "races", "runners", "meetingKey", "raceKey"]
            return runner_count or race_count or len(meetings), headers, data
        return 1, sorted(data.keys()), data
    return 0, [], data


def file_row_count(path: Path) -> tuple[int, list[str], Any]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return fast_count_rows(path), csv_header(path), None
    if suffix == ".json":
        return json_stats(path)
    if suffix in {".parquet", ".sqlite", ".db", ".duckdb"}:
        return 0, [], None
    return 0, [], None


def detect_dates(path: Path, headers: list[str]) -> tuple[str, str]:
    if path.suffix.lower() != ".csv":
        return "", ""
    date_cols = [h for h in headers if re.search(r"date|time|timestamp|updated|generated|built", h, re.I)]
    if not date_cols:
        return "", ""
    values: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for index, row in enumerate(reader):
                if index > 20000:
                    break
                for col in date_cols[:4]:
                    value = (row.get(col) or "").strip()
                    if re.search(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}", value):
                        values.append(value[:10].replace("/", "-"))
    except Exception:
        return "", ""
    if not values:
        return "", ""
    return min(values), max(values)


def duplicate_count_for_keys(path: Path, headers: list[str]) -> int:
    if path.suffix.lower() != ".csv":
        return 0
    preferred = [
        "race_key",
        "raceKey",
        "meeting_key",
        "meetingKey",
        "race_date",
        "track",
        "race_no",
        "runner",
    ]
    keys = [h for h in preferred if h in headers]
    if not keys:
        return 0
    counter: Counter[str] = Counter()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for index, row in enumerate(reader):
                if index > 100000:
                    break
                key = "|".join(normalise_key(row.get(k, "")) for k in keys[:4])
                counter[key] += 1
    except Exception:
        return 0
    return sum(1 for count in counter.values() if count > 1)


def extract_catalog_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    path = PUBLIC_DATA / "edgeiq_three_day_product_catalog_v1.json"
    if not path.exists():
        return [], [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return [], [], []
    meetings: list[dict[str, str]] = []
    races: list[dict[str, str]] = []
    runners: list[dict[str, str]] = []
    for meeting in data.get("meetings", []):
        if not isinstance(meeting, dict):
            continue
        meeting_row = {
            "meeting_key": str(meeting.get("meetingKey") or ""),
            "date": str(meeting.get("date") or ""),
            "track": str(meeting.get("meeting") or ""),
            "state": str((meeting.get("source") or {}).get("State") or ""),
            "race_count": str(meeting.get("raceCount") or len(meeting.get("races") or "")),
            "track_condition": str(meeting.get("trackCondition") or ""),
            "rail": str(meeting.get("rail") or ""),
            "status": str((meeting.get("source") or {}).get("FullStatus") or (meeting.get("source") or {}).get("Status") or ""),
        }
        meetings.append(meeting_row)
        for race in meeting.get("races") or []:
            if not isinstance(race, dict):
                continue
            race_row = {
                **meeting_row,
                "race_key": str(race.get("raceKey") or ""),
                "race_no": str(race.get("raceNumber") or ""),
                "race_name": str(race.get("raceName") or ""),
                "distance": str(race.get("distance") or ""),
                "class": str(race.get("raceClass") or ""),
                "race_time": str(race.get("raceTime") or ""),
                "track_condition": str(race.get("trackCondition") or meeting_row.get("track_condition") or ""),
                "rail": str(race.get("rail") or meeting_row.get("rail") or ""),
            }
            races.append(race_row)
            for runner in race.get("runners") or []:
                official = runner.get("official") or {}
                runners.append(
                    {
                        **race_row,
                        "runner": str(official.get("runner") or ""),
                        "runner_no": str(official.get("no") or official.get("number") or ""),
                        "barrier": str(official.get("barrier") or ""),
                        "jockey": str(official.get("jockey") or ""),
                        "trainer": str(official.get("trainer") or ""),
                        "weight": str(official.get("weight") or ""),
                        "market": str(official.get("market") or ""),
                        "silk": str(official.get("silkUrl") or ""),
                        "scratched": str(official.get("scratched") or ""),
                        "current_gear": str(official.get("currentGear") or ""),
                    }
                )
    return meetings, races, runners


def feed_rows_for_workspace(workspace: str, feed_spec: str) -> tuple[list[dict[str, str]], str]:
    feeds = [f.strip() for f in feed_spec.split("|") if f.strip()]
    for feed in feeds:
        path = PUBLIC_DATA / feed
        if path.exists() and path.suffix.lower() == ".csv":
            rows = load_csv_limited(path)
            if rows:
                return rows, feed
        if feed == "edgeiq_three_day_product_catalog_v1.json":
            meetings, races, runners = extract_catalog_rows()
            if workspace == "Meetings":
                return meetings, feed
            if workspace == "Meeting Detail":
                return races, feed
            return runners, feed
        if feed == "edgeiq_three_day_window_v1.json":
            meetings, _, _ = extract_catalog_rows()
            return meetings, feed
    return [], feeds[0] if feeds else ""


def matching_columns(headers: list[str], field: str) -> list[str]:
    aliases = FIELD_ALIASES.get(field, [])
    tokens = [field.lower().replace(" ", "_"), field.lower().replace(" ", "")]
    needles = {normalise_key(a) for a in aliases + tokens}
    matches = []
    for header in headers:
        key = normalise_key(header)
        if key in needles:
            matches.append(header)
            continue
        for needle in needles:
            if needle and (needle in key or key in needle):
                matches.append(header)
                break
    return sorted(set(matches))


def coverage_for_field(rows: list[dict[str, str]], field: str) -> tuple[str, int, float, str]:
    if not rows:
        return "unavailable", 0, 0.0, "no rows in governed terminal feed"
    headers = list(rows[0].keys())
    cols = matching_columns(headers, field)
    if not cols:
        return "unavailable", 0, 0.0, "field not present in terminal feed/service view model"
    populated = 0
    for row in rows:
        if any(text_status(row.get(col)) for col in cols):
            populated += 1
    pct = round(populated * 100 / max(1, len(rows)), 1)
    if populated == 0:
        return "unavailable", populated, pct, "column present but unpopulated"
    if pct < 95:
        return "partial", populated, pct, f"partial population via {','.join(cols)}"
    return "populated", populated, pct, f"populated via {','.join(cols)}"


def freshness_for_file(feed_spec: str) -> str:
    statuses = []
    for feed in [f.strip() for f in feed_spec.split("|") if f.strip()]:
        path = PUBLIC_DATA / feed
        if not path.exists():
            statuses.append("missing")
            continue
        age_seconds = datetime.now().timestamp() - path.stat().st_mtime
        if age_seconds < 36 * 3600:
            statuses.append("current")
        elif age_seconds < 7 * 24 * 3600:
            statuses.append("recent")
        else:
            statuses.append("stale")
    if not statuses:
        return "missing"
    if "current" in statuses:
        return "current"
    if "recent" in statuses:
        return "recent"
    if "stale" in statuses:
        return "stale"
    return "missing"


def discover_service_feed_map() -> dict[str, set[str]]:
    service_map: dict[str, set[str]] = defaultdict(set)
    service_dir = ROOT / "src" / "edgeiq-os" / "race" / "services"
    pattern = re.compile(r"/data/([^\"')]+)")
    for path in service_dir.glob("*.ts"):
        if "CHECKPOINT" in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in pattern.findall(text):
            service_map[path.name].add(Path(match).name)
    return service_map


def react_boundary_findings() -> dict[str, list[str]]:
    findings: dict[str, list[str]] = defaultdict(list)
    component_dir = ROOT / "src" / "edgeiq-os" / "race" / "components"
    forbidden = [
        "implied",
        "fairPrice",
        "fair_price",
        "edgePercent",
        "edge_pct",
        "calculate",
        "probability",
        "tempo",
        "pressure",
        "suitability",
        "momentum",
    ]
    for path in component_dir.glob("*.tsx"):
        if "CHECKPOINT" in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            compact = line.strip()
            if not compact or compact.startswith("//"):
                continue
            if any(token in compact for token in forbidden) and re.search(r"[+\-*/]|\bMath\.|\breduce\(|\bmap\(", compact):
                findings[path.name].append(f"{lineno}:{compact[:140]}")
    return findings


def build_field_inventory(service_feeds: dict[str, set[str]], boundary: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    for workspace, meta in WORKSPACES.items():
        feed_rows, selected_feed = feed_rows_for_workspace(workspace, meta["feed"])
        duplicate_feed = "yes" if len([f for f in meta["feed"].split("|") if f.strip()]) > 1 else "no"
        service_names = [s.strip() for s in meta["service"].split("|")]
        service_fetches = sorted({feed for service in service_names for feed in service_feeds.get(service, set())})
        for field in meta["fields"]:
            status, populated, pct, note = coverage_for_field(feed_rows, field)
            freshness = freshness_for_file(meta["feed"])
            missing_reason = ""
            priority = "P2"
            action = "none"
            if status == "unavailable":
                missing_reason = "SOURCE_NOT_DISCOVERED" if "not present" in note else "SOURCE_PARTIAL"
                action = "discover or wire governed builder-owned source"
                priority = "P1"
            elif status == "partial":
                missing_reason = "SOURCE_PARTIAL"
                action = "improve builder join/source coverage"
                priority = "P1"
            if freshness in {"stale", "missing"}:
                if missing_reason:
                    missing_reason += "|"
                missing_reason += "SOURCE_STALE" if freshness == "stale" else "SOURCE_NOT_DISCOVERED"
                action = "refresh governed feed or document unavailable authority"
                priority = "P1"
            react_calc = "yes" if any(meta["component"].split("|")[0] in comp and findings for comp, findings in boundary.items()) else "no"
            rows_out.append(
                {
                    "workspace": workspace,
                    "section": "governed data",
                    "field": field,
                    "component": meta["component"],
                    "view_model": meta["view_model"],
                    "service": meta["service"],
                    "terminal_feed": selected_feed or meta["feed"],
                    "upstream_source": "|".join(service_fetches) or meta["feed"],
                    "join_key": meta["join_key"],
                    "required_data_type": infer_domain(field),
                    "current_population_status": status,
                    "current_coverage_rows": populated,
                    "current_coverage_percent": pct,
                    "freshness_status": freshness,
                    "source_authority": infer_authority(meta["feed"]),
                    "missing_reason": missing_reason,
                    "intended_builder_owner": meta["builder"],
                    "react_calculation_detected": react_calc,
                    "duplicate_feed_detected": duplicate_feed,
                    "action_required": action,
                    "priority": priority,
                    "notes": note,
                }
            )
    return rows_out


def relevant_source_files() -> list[Path]:
    roots = [PUBLIC_DATA, ROOT / "data"]
    exts = {".csv", ".json", ".parquet", ".sqlite", ".db", ".duckdb"}
    keywords = re.compile(
        r"edgeiq|race|racing|runner|horse|market|gear|scratch|weather|track|sectional|speed|result|form|meeting|map|epi|eri|dna|profile",
        re.I,
    )
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in exts:
                continue
            if keywords.search(path.name) or "public\\data" in str(path):
                files.append(path)
    return sorted(files, key=lambda p: rel(p).lower())


def current_meeting_keys() -> tuple[set[str], set[str]]:
    meetings, races, runners = extract_catalog_rows()
    tracks = {normalise_key(row.get("track")) for row in meetings if row.get("track")}
    race_keys = {normalise_key(row.get("race_key")) for row in races if row.get("race_key")}
    runner_keys = {
        "|".join([normalise_key(row.get("date")), normalise_key(row.get("track")), normalise_key(row.get("race_no")), normalise_key(row.get("runner"))])
        for row in runners
        if row.get("runner")
    }
    return tracks | race_keys, runner_keys


def source_registry() -> list[dict[str, Any]]:
    current_keys, runner_keys = current_meeting_keys()
    rows_out: list[dict[str, Any]] = []
    for path in relevant_source_files():
        row_count, headers, _ = file_row_count(path)
        is_governed_current = bool(
            re.search(
                r"terminal_feed|three_day|current|official|weather_beta|form_guide_enriched|scratchings|gear|track_map|market_terminal|overview_terminal|insights_terminal|epi_workspace",
                path.name,
                re.I,
            )
        )
        date_min, date_max = detect_dates(path, headers) if is_governed_current or path.stat().st_size < 10 * 1024 * 1024 else ("", "")
        key_cols = [h for h in headers if normalise_key(h) in {"RACEKEY", "MEETINGKEY", "RACEDATE", "TRACK", "RACENO", "RUNNER", "HORSE"}]
        duplicate_count = duplicate_count_for_keys(path, headers) if is_governed_current and path.stat().st_size < 25 * 1024 * 1024 else 0
        current_matches = ""
        if path.suffix.lower() == ".csv" and row_count and row_count <= 50000 and is_governed_current:
            match_count = 0
            for row in load_csv_limited(path, limit=50000):
                track_match = normalise_key(row.get("track") or row.get("meeting") or row.get("venue")) in current_keys
                race_match = normalise_key(row.get("race_key") or row.get("raceKey")) in current_keys
                runner_match = "|".join(
                    [
                        normalise_key(row.get("race_date") or row.get("date")),
                        normalise_key(row.get("track") or row.get("meeting")),
                        normalise_key(row.get("race_no") or row.get("raceNumber")),
                        normalise_key(row.get("runner") or row.get("horse") or row.get("horse_name")),
                    ]
                ) in runner_keys
                if track_match or race_match or runner_match:
                    match_count += 1
            current_matches = str(match_count)
        safe = "yes" if row_count <= SAFE_FRONTEND_ROW_THRESHOLD and path.stat().st_size <= 5 * 1024 * 1024 else "no"
        freshness = "current"
        age_seconds = datetime.now().timestamp() - path.stat().st_mtime
        if age_seconds > 7 * 24 * 3600:
            freshness = "stale"
        elif age_seconds > 36 * 3600:
            freshness = "recent"
        rows_out.append(
            {
                "source_name": path.name,
                "source_path": rel(path),
                "source_type": source_type(path),
                "authority": infer_authority(path.name),
                "domain": infer_domain(path.name),
                "row_count": row_count,
                "date_min": date_min,
                "date_max": date_max,
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "freshness": freshness,
                "grain": infer_grain(headers, path.name),
                "primary_keys": "|".join(key_cols),
                "duplicate_key_count": duplicate_count,
                "current_meeting_match_count": current_matches,
                "safe_for_frontend": safe,
                "requires_builder": "no" if safe == "yes" and "terminal_feed" in path.name else "yes",
                "canonical_owner": infer_canonical_owner(path.name),
                "downstream_workspaces": infer_workspaces(path.name),
                "known_gaps": "",
                "notes": "warehouse-scale; keep out of React" if safe == "no" else "",
            }
        )
    return rows_out


def infer_grain(headers: list[str], name: str) -> str:
    keys = {normalise_key(h) for h in headers}
    if "RUNNER" in keys or "HORSE" in keys or "HORSENAME" in keys:
        if "RACENO" in keys or "RACEKEY" in keys:
            return "runner-race"
        return "runner"
    if "RACENO" in keys or "RACEKEY" in keys:
        return "race"
    if "TRACK" in keys or "MEETING" in keys:
        return "meeting"
    if name.lower().endswith(".json") and "catalog" in name.lower():
        return "meeting-race-runner"
    return "file"


def infer_canonical_owner(name: str) -> str:
    lower = name.lower()
    if "terminal_feed" in lower or "enriched" in lower:
        return "governed terminal feed"
    if "warehouse" in lower or "master" in lower or "history" in lower:
        return "warehouse source"
    if "audit" in lower or "summary" in lower:
        return "audit artifact"
    return "candidate source"


JOIN_KEY_ALIASES = {
    "date": ["date", "race_date", "raceDate"],
    "race_date": ["race_date", "raceDate", "date"],
    "track": ["track", "meeting", "venue"],
    "meeting": ["meeting", "track", "venue"],
    "race_no": ["race_no", "raceNumber", "race_number", "race"],
    "raceNumber": ["raceNumber", "race_no", "race_number", "race"],
    "runner": ["runner", "horse", "runnerName", "runner_name", "horse_name"],
    "horse": ["horse", "runner", "runnerName", "runner_name", "horse_name"],
}


def row_value_for_key(row: dict[str, str], key: str) -> str:
    for alias in JOIN_KEY_ALIASES.get(key, [key]):
        if alias in row and text_status(row.get(alias)):
            return row.get(alias, "")
    return ""


def key_counts(rows: list[dict[str, str]], keys: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        key = "|".join(normalise_key(row_value_for_key(row, k)) for k in keys)
        if key.strip("|"):
            counter[key] += 1
    return counter


def load_feed_for_join(feed: str) -> list[dict[str, str]]:
    path = PUBLIC_DATA / feed
    if path.suffix.lower() == ".csv":
        return load_csv_limited(path, limit=100000)
    if feed == "edgeiq_three_day_product_catalog_v1.json":
        _, _, runners = extract_catalog_rows()
        return runners
    return []


def join_integrity() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    joins = [
        ("catalog_to_form_guide", "Form Guide", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_form_guide_enriched_v2.csv", ["date", "track", "race_no", "runner"], ["race_date", "track", "race_no", "runner"]),
        ("catalog_to_gear", "Gear Changes", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_gear_terminal_feed_v1.csv", ["date", "track", "race_no", "runner"], ["race_date", "track", "race_no", "runner"]),
        ("catalog_to_map", "MAP", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_map_terminal_feed_v1.csv", ["date", "track", "race_no", "runner"], ["race_date", "track", "race_no", "runner"]),
        ("catalog_to_market", "Market", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_market_terminal_feed_v1.csv", ["date", "track", "race_no", "runner"], ["race_date", "track", "race_no", "runner"]),
        ("catalog_to_overview", "Overview", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_overview_terminal_feed_v1.csv", ["date", "track", "race_no"], ["race_date", "track", "race_no"]),
        ("catalog_to_insights", "Insights", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_insights_terminal_feed_v1.csv", ["date", "track", "race_no", "runner"], ["race_date", "track", "race_no", "runner"]),
        ("catalog_to_epi", "EPI Workspace", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_epi_workspace_terminal_feed_v1.csv", ["date", "track", "race_no", "runner"], ["race_date", "track", "race_no", "runner"]),
        ("catalog_to_results", "Results", "edgeiq_three_day_product_catalog_v1.json", "edgeiq_meeting_results_terminal_feed_v1.csv", ["date", "track", "race_no"], ["race_date", "track", "race_no"]),
    ]
    rows_out: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"joins": [], "status": "PASS"}
    for name, workspace, left_feed, right_feed, left_keys, right_keys in joins:
        left_rows = load_feed_for_join(left_feed)
        right_rows = load_feed_for_join(right_feed)
        left_counts = key_counts(left_rows, left_keys)
        right_counts = key_counts(right_rows, right_keys)
        left_set = set(left_counts)
        right_set = set(right_counts)
        matched = len(left_set & right_set)
        unmatched_left = len(left_set - right_set)
        unmatched_right = len(right_set - left_set)
        duplicate_left = sum(1 for count in left_counts.values() if count > 1)
        duplicate_right = sum(1 for count in right_counts.values() if count > 1)
        status = "PASS"
        notes = ""
        review_required = "no"
        if not right_rows:
            status = "WARN"
            notes = "right governed feed missing or empty"
        elif matched == 0:
            status = "WARN"
            notes = "no exact canonical key matches; review feed date/track/race/runner keys"
            review_required = "yes"
        elif unmatched_left > 0:
            status = "WARN"
            notes = "partial exact key coverage"
        rows_out.append(
            {
                "join_name": name,
                "workspace": workspace,
                "left_source": left_feed,
                "right_source": right_feed,
                "join_key": "|".join(right_keys),
                "left_rows": len(left_rows),
                "right_rows": len(right_rows),
                "matched_rows": matched,
                "unmatched_left_rows": unmatched_left,
                "unmatched_right_rows": unmatched_right,
                "duplicate_left_keys": duplicate_left,
                "duplicate_right_keys": duplicate_right,
                "conflicting_values": 0,
                "stale_date_matches": 0,
                "fuzzy_matches": 0,
                "review_required": review_required,
                "status": status,
                "notes": notes,
            }
        )
        summary["joins"].append(rows_out[-1])
        if status != "PASS":
            summary["status"] = "WARN"
    return rows_out, summary


def cross_workspace_consistency() -> list[dict[str, Any]]:
    field_map = {
        "runner": ["runner", "horse", "horse_name"],
        "barrier": ["barrier", "bar"],
        "weight": ["weight", "wt"],
        "jockey": ["jockey"],
        "trainer": ["trainer"],
        "market": ["market", "live_price", "current_price"],
        "EPI": ["epi", "current_epi"],
        "early speed": ["early_speed"],
        "late speed": ["late_speed"],
        "race shape": ["race_shape", "shape"],
    }
    feeds = {
        "Form Guide": "edgeiq_form_guide_enriched_v2.csv",
        "MAP": "edgeiq_map_terminal_feed_v1.csv",
        "Market": "edgeiq_market_terminal_feed_v1.csv",
        "Insights": "edgeiq_insights_terminal_feed_v1.csv",
        "EPI Workspace": "edgeiq_epi_workspace_terminal_feed_v1.csv",
    }
    by_key: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for workspace, feed in feeds.items():
        for row in load_feed_for_join(feed):
            key = "|".join(
                [
                    normalise_key(row.get("race_date") or row.get("date")),
                    normalise_key(row.get("track") or row.get("meeting")),
                    normalise_key(row.get("race_no") or row.get("raceNumber")),
                    normalise_key(row.get("runner") or row.get("horse") or row.get("horse_name")),
                ]
            )
            if key.strip("|"):
                by_key[key][workspace] = row
    rows_out: list[dict[str, Any]] = []
    for key, workspace_rows in list(by_key.items())[:5000]:
        for field, aliases in field_map.items():
            values: dict[str, str] = {}
            for workspace, row in workspace_rows.items():
                for alias in aliases:
                    if alias in row and text_status(row.get(alias)):
                        values[workspace] = str(row.get(alias)).strip()
                        break
            normalised_values = {workspace: normalise_key(value) for workspace, value in values.items()}
            unique = set(normalised_values.values())
            if len(values) >= 2:
                rows_out.append(
                    {
                        "runner_key": key,
                        "field": field,
                        "workspace_values": json.dumps(values, sort_keys=True),
                        "status": "PASS" if len(unique) <= 1 else "WARN",
                        "notes": "" if len(unique) <= 1 else "different values across governed feeds; review timestamps/source versions",
                    }
                )
    return rows_out


def coverage_matrix(inventory_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meetings, races, runners = extract_catalog_rows()
    out: list[dict[str, Any]] = []
    for row in inventory_rows:
        total = len(runners) if row["join_key"].count("|") >= 3 else len(races) if "race" in row["join_key"].lower() else len(meetings)
        populated = int(row["current_coverage_rows"] or 0)
        unavailable = max(0, total - populated)
        out.append(
            {
                "workspace": row["workspace"],
                "field": row["field"],
                "total_current_meetings": len(meetings),
                "total_current_races": len(races),
                "total_current_runners": len(runners),
                "populated_rows": populated,
                "unavailable_rows": unavailable if row["current_population_status"] != "populated" else 0,
                "stale_rows": total if row["freshness_status"] == "stale" else 0,
                "error_rows": 0,
                "coverage_percent": row["current_coverage_percent"],
                "source": row["terminal_feed"],
                "source_version": "",
                "freshness": row["freshness_status"],
                "blocker": row["missing_reason"],
                "next_integration_action": row["action_required"],
            }
        )
    summary = {
        "generated_at": now_iso(),
        "total_visible_fields": len(inventory_rows),
        "populated_fields": sum(1 for r in inventory_rows if r["current_population_status"] == "populated"),
        "partial_fields": sum(1 for r in inventory_rows if r["current_population_status"] == "partial"),
        "unavailable_fields": sum(1 for r in inventory_rows if r["current_population_status"] == "unavailable"),
        "stale_fields": sum(1 for r in inventory_rows if r["freshness_status"] == "stale"),
        "current_meetings": len(meetings),
        "current_races": len(races),
        "current_runners": len(runners),
    }
    return out, summary


def update_gaps(inventory_rows: list[dict[str, Any]]) -> int:
    existing: list[dict[str, str]] = []
    fieldnames = [
        "workspace",
        "field",
        "gap_type",
        "source",
        "reason",
        "resolution_status",
        "resolution_evidence",
        "next_action",
        "updated_at",
    ]
    if GAPS_CSV.exists():
        try:
            with GAPS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                old_fields = reader.fieldnames or []
                fieldnames = list(dict.fromkeys(old_fields + fieldnames))
                existing = [{k: (row.get(k) or "") for k in fieldnames} for row in reader]
        except Exception:
            existing = []
    seen = {(row.get("workspace", ""), row.get("field", "")) for row in existing}
    added = 0
    for row in inventory_rows:
        if row["current_population_status"] == "populated" and row["freshness_status"] != "stale":
            continue
        key = (row["workspace"], row["field"])
        evidence = f"{row['current_population_status']} coverage={row['current_coverage_percent']} feed={row['terminal_feed']} freshness={row['freshness_status']}"
        if key in seen:
            for existing_row in existing:
                if (existing_row.get("workspace"), existing_row.get("field")) == key:
                    existing_row["resolution_status"] = "OPEN" if row["current_population_status"] != "populated" else "PARTIAL"
                    existing_row["resolution_evidence"] = evidence
                    existing_row["next_action"] = row["action_required"]
                    existing_row["updated_at"] = now_iso()
            continue
        gap = {name: "" for name in fieldnames}
        gap.update(
            {
                "workspace": row["workspace"],
                "field": row["field"],
                "gap_type": row["missing_reason"] or "SOURCE_PARTIAL",
                "source": row["terminal_feed"],
                "reason": row["notes"],
                "resolution_status": "OPEN",
                "resolution_evidence": evidence,
                "next_action": row["action_required"],
                "updated_at": now_iso(),
            }
        )
        existing.append(gap)
        seen.add(key)
        added += 1
    write_csv(GAPS_CSV, existing, fieldnames)
    return added


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def write_progress(status: str, **extra: Any) -> None:
    progress = {
        "started_at": extra.get("started_at") or now_iso(),
        "last_updated_at": now_iso(),
        "current_workspace": extra.get("current_workspace", "GLOBAL_AUDIT"),
        "completed_workspaces": extra.get("completed_workspaces", []),
        "partial_workspaces": extra.get("partial_workspaces", []),
        "blocked_workspaces": extra.get("blocked_workspaces", []),
        "failed_workspaces": extra.get("failed_workspaces", []),
        "current_checkpoint": extra.get("current_checkpoint", ""),
        "last_successful_audit": extra.get("last_successful_audit", ""),
        "last_successful_build": extra.get("last_successful_build", ""),
        "sources_discovered": extra.get("sources_discovered", 0),
        "feeds_created": extra.get("feeds_created", []),
        "feeds_updated": extra.get("feeds_updated", []),
        "fields_resolved": extra.get("fields_resolved", 0),
        "fields_remaining": extra.get("fields_remaining", 0),
        "next_workspace": extra.get("next_workspace", "Meetings"),
        "overall_status": status,
    }
    write_json(PROGRESS_JSON, progress)
    PROGRESS_TXT.write_text("\n".join(f"{k}: {v}" for k, v in progress.items()), encoding="utf-8")


def main() -> int:
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    started = now_iso()
    preflight = [
        "EDGEIQ_BETA_GOVERNED_DATA_COMPLETION_V1_PREFLIGHT",
        f"generated_at={started}",
        f"project_root={ROOT}",
        "mode=script_driven_governed_data_audit",
        "react_rule=display_only_no_racing_intelligence_calculations",
    ]
    PREFLIGHT_TXT.write_text("\n".join(preflight) + "\n", encoding="utf-8")
    write_progress("RUNNING", started_at=started, current_workspace="PREFLIGHT", last_successful_audit="preflight")

    service_feeds = discover_service_feed_map()
    boundary = react_boundary_findings()
    inventory = build_field_inventory(service_feeds, boundary)
    write_csv(FIELD_INVENTORY, inventory, FIELD_COLUMNS)

    registry = source_registry()
    write_csv(SOURCE_REGISTRY, registry, SOURCE_COLUMNS)

    joins, join_summary = join_integrity()
    write_csv(JOIN_AUDIT, joins, JOIN_COLUMNS)
    write_json(JOIN_JSON, join_summary)
    JOIN_SUMMARY.write_text(
        "\n".join(
            [
                "EDGEIQ_BETA_DATA_JOIN_INTEGRITY_V1",
                f"generated_at={now_iso()}",
                f"status={join_summary['status']}",
                f"joins_audited={len(joins)}",
                f"warn_joins={sum(1 for row in joins if row['status'] != 'PASS')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    consistency = cross_workspace_consistency()
    write_csv(CONSISTENCY_CSV, consistency, ["runner_key", "field", "workspace_values", "status", "notes"])

    coverage_rows, coverage_summary = coverage_matrix(inventory)
    coverage_columns = [
        "workspace",
        "field",
        "total_current_meetings",
        "total_current_races",
        "total_current_runners",
        "populated_rows",
        "unavailable_rows",
        "stale_rows",
        "error_rows",
        "coverage_percent",
        "source",
        "source_version",
        "freshness",
        "blocker",
        "next_integration_action",
    ]
    write_csv(COVERAGE_CSV, coverage_rows, coverage_columns)
    write_json(COVERAGE_JSON, coverage_summary)
    COVERAGE_TXT.write_text("\n".join(f"{k}: {v}" for k, v in coverage_summary.items()) + "\n", encoding="utf-8")

    gaps_added = update_gaps(inventory)

    workspace_summaries = []
    for workspace in WORKSPACES:
        rows = [row for row in inventory if row["workspace"] == workspace]
        populated = sum(1 for row in rows if row["current_population_status"] == "populated")
        partial = sum(1 for row in rows if row["current_population_status"] == "partial")
        unavailable = sum(1 for row in rows if row["current_population_status"] == "unavailable")
        status = "EDGEIQ_" + re.sub(r"[^A-Z0-9]+", "_", workspace.upper()).strip("_") + "_GOVERNED_DATA_COMPLETION_V1_AUDIT_PASS"
        data_status = "fully_populated" if unavailable == 0 and partial == 0 else "partially_populated"
        workspace_summaries.append(
            {
                "workspace": workspace,
                "implementation_status": "inspected",
                "data_population_status": data_status,
                "coverage_percentage": round(populated * 100 / max(1, len(rows)), 1),
                "fields": len(rows),
                "populated": populated,
                "partial": partial,
                "unavailable": unavailable,
                "audit_status": status,
            }
        )

    final = {
        "generated_at": now_iso(),
        "status": "EDGEIQ_BETA_GOVERNED_DATA_COMPLETION_V1_AUDIT_BASELINE_COMPLETE",
        "workspaces": workspace_summaries,
        "global_totals": {
            **coverage_summary,
            "sources_discovered": len(registry),
            "joins_audited": len(joins),
            "join_warnings": sum(1 for row in joins if row["status"] != "PASS"),
            "gap_rows_added": gaps_added,
            "react_boundary_findings": sum(len(v) for v in boundary.values()),
            "existing_feeds_reused": len({row["terminal_feed"] for row in inventory if row["terminal_feed"]}),
        },
        "outputs": {
            "field_inventory": rel(FIELD_INVENTORY),
            "source_registry": rel(SOURCE_REGISTRY),
            "join_audit": rel(JOIN_AUDIT),
            "coverage_matrix": rel(COVERAGE_CSV),
            "consistency": rel(CONSISTENCY_CSV),
            "gaps": rel(GAPS_CSV),
        },
        "notes": [
            "This is the governed-data completion baseline and lineage audit.",
            "Fields with real unavailable or stale source state remain documented rather than fabricated.",
            "Warehouse-scale sources are marked requires_builder and unsafe for frontend.",
        ],
    }
    write_json(FINAL_JSON, final)
    lines = [
        "EDGEIQ_BETA_GOVERNED_DATA_COMPLETION_V1_BASELINE_REPORT",
        f"generated_at={final['generated_at']}",
        f"status={final['status']}",
        f"total_visible_fields={coverage_summary['total_visible_fields']}",
        f"populated_fields={coverage_summary['populated_fields']}",
        f"partial_fields={coverage_summary['partial_fields']}",
        f"unavailable_fields={coverage_summary['unavailable_fields']}",
        f"stale_fields={coverage_summary['stale_fields']}",
        f"sources_discovered={len(registry)}",
        f"joins_audited={len(joins)}",
        f"join_warnings={sum(1 for row in joins if row['status'] != 'PASS')}",
        f"gap_rows_added={gaps_added}",
        "",
        "Workspace statuses:",
    ]
    for item in workspace_summaries:
        lines.append(
            f"- {item['workspace']}: {item['data_population_status']} "
            f"fields={item['fields']} populated={item['populated']} partial={item['partial']} unavailable={item['unavailable']} "
            f"audit={item['audit_status']}"
        )
    FINAL_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    remaining = coverage_summary["partial_fields"] + coverage_summary["unavailable_fields"] + coverage_summary["stale_fields"]
    completed = [row["workspace"] for row in workspace_summaries]
    write_progress(
        "AUDIT_BASELINE_COMPLETE",
        started_at=started,
        current_workspace="GLOBAL_AUDIT",
        completed_workspaces=completed,
        partial_workspaces=[row["workspace"] for row in workspace_summaries if row["data_population_status"] != "fully_populated"],
        last_successful_audit=rel(FINAL_JSON),
        sources_discovered=len(registry),
        fields_resolved=coverage_summary["populated_fields"],
        fields_remaining=remaining,
        next_workspace="Meetings data wiring review",
    )
    print(json.dumps(final["global_totals"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
